"""Small explicit CLI. JSON goes to stdout; runtime progress goes to stderr."""

import argparse
import json


def main(argv=None):
    parser = argparse.ArgumentParser(prog="fpl3")
    sub = parser.add_subparsers(dest="action", required=True)
    doctor = sub.add_parser("doctor", help="Inspect environment; no network or model inference")
    doctor.add_argument("--out")
    doctor.add_argument("--local", help="Also inspect the configured P1 Conda worker")
    imp = sub.add_parser("import-p1")
    imp.add_argument("--local", required=True)
    imp.add_argument("--out", required=True)
    imp.add_argument("--third-party", required=True)
    run = sub.add_parser("run-p1")
    run.add_argument("--local", required=True)
    run.add_argument("--out", required=True)
    run.add_argument("--fresh", action="store_true")
    verify = sub.add_parser("verify-migration")
    verify.add_argument("--local", required=True)
    verify.add_argument("--run", required=True)
    verify.add_argument("--out", required=True)
    numerical = sub.add_parser("check-p1-numerics")
    numerical.add_argument("--local", required=True)
    numerical.add_argument("--out", required=True)
    dahia = sub.add_parser("dahia-check")
    dahia.add_argument("--source", required=True)
    dahia.add_argument("--out", required=True)
    dahia.add_argument("--network", action="store_true")
    supervisor = sub.add_parser("supervisor-p1", help="Frozen Step 02 P1 protocol; no threshold tuning on evaluation")
    supervisor.add_argument("phase", choices=("prepare", "run", "report"))
    supervisor.add_argument("--local", required=True)
    supervisor.add_argument("--out", required=True)
    supervisor.add_argument("--specification")
    supervisor.add_argument("--prepared")
    supervisor.add_argument("--role", choices=("development", "evaluation"))
    supervisor.add_argument("--development-run")
    supervisor.add_argument("--run")
    args = parser.parse_args(argv)
    if args.action == "doctor":
        from .runtime import doctor
        if args.local:
            from .runner import doctor_with_workers
            result = doctor_with_workers(args.local)
        else:
            result = doctor("dev")
        if args.out:
            from .io import write_json
            write_json(args.out, result)
    elif args.action == "import-p1":
        from .importer import import_p1
        result = import_p1(args.local, args.out, args.third_party)
    elif args.action == "run-p1":
        from .runner import run_p1
        result = run_p1(args.local, args.out, args.fresh)
    elif args.action == "verify-migration":
        from .verification import verify_migration
        result = verify_migration(args.local, args.run, args.out)
    elif args.action == "check-p1-numerics":
        from .runner import check_p1_via_worker
        result = check_p1_via_worker(args.local, args.out)
    elif args.action == "supervisor-p1":
        from .supervisor import prepare, run_supervisor
        if args.phase == "prepare":
            if not args.specification:
                parser.error("prepare requires --specification")
            result = prepare(args.local, args.specification, args.out)
        elif args.phase == "run":
            if not args.prepared or not args.role:
                parser.error("run requires --prepared and --role")
            result = run_supervisor(args.prepared, args.local, args.role, args.out, args.development_run)
        else:
            from .supervisor_report import write_report
            if not args.prepared or not args.run:
                parser.error("report requires --prepared and --run")
            result = write_report(args.prepared, args.local, args.run, args.out)
    else:
        from .dahia import check_artifacts
        result = check_artifacts(args.source, args.out, args.network)
    print(json.dumps(result, indent=2, allow_nan=False))
    if args.action == "run-p1" and (result.get("run_status") != "success" or result["success"] != result["planned"]):
        return 2
    if args.action == "verify-migration" and not result["approved"]:
        return 2
    if args.action == "supervisor-p1" and args.phase != "prepare" and not result["approved"]:
        return 2
    return 0
