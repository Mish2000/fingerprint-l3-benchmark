# Environment and execution

## Installed profiles

The project standard is Miniconda with two project-local environments, checked on
2026-09-13. [Environment policy](environment-policy.md) explains the choice and
future upgrades. Windows x86-64 is the tested platform.

| Profile | Python | Installed role/dependencies |
|---|---|---|
| `.conda/dev` | 3.13.15, standard GIL | Coordinator, NumPy 2.5.2, pytest 9.1.1, Ruff 0.16.5 |
| `.conda/p1` | 3.10.21 | CPU worker; NumPy 1.26.4, Torch 1.13.0, Torchvision 0.14.0, OpenCV contrib 3.4.18.65, SciPy 1.15.3 |

P1 uses four Torch threads. Miniconda's base manages environments; no project
packages are installed into base. Global shell, Python, CUDA and driver settings
are unchanged. The local PyCharm project selects the Conda development interpreter;
machine-specific IDE settings remain ignored.

## PowerShell setup and checks

Run from the project root:

```powershell
.\scripts\bootstrap.ps1
.\scripts\bootstrap.ps1 -VerifyOnly
.\scripts\test.ps1
.\scripts\fpl3.ps1 doctor
```

Use `bootstrap.ps1 -CondaExe 'path\to\conda.exe'` when Miniconda is not discovered.
Bootstrap creates missing prefixes from `environments/locks/*-win-64.explicit.txt`.
It installs the pip-only P1 lock with `--no-deps`, then installs this package with
`--no-deps -e .` into each environment. Native Conda and pip packages have separate
ownership. Existing profiles must have the expected Python version. `-VerifyOnly`
checks both Python versions, `pip check`, installed metadata uniqueness and pip's
code/metadata version without installation. It is not a complete package-lock
comparison or a model test. Fresh P1 creation from the final lock was exercised;
both installed native package inventories were also compared exactly to the locks.

The scripts use `conda run`, so activation is automatic for the command. In a
Conda-enabled interactive shell, `conda activate .\.conda\dev` is also available.
Configure IDEs to use `.conda/dev/python.exe` with Miniconda's Conda executable.
Direct interpreter invocation may omit DLL search-path activation on Windows;
use the supplied wrappers for reproducible numerical execution.

`test.ps1` runs the synthetic suite and Ruff. Tests need neither SD300,
models nor network. `doctor` reports interpreter, package paths, versions and
isolation without inference or network. With local configuration it also launches
a P1 worker to inspect that environment separately:

```powershell
.\scripts\fpl3.ps1 doctor --local workspace\local.json
```

## Private configuration and import

`workspace/local.json` uses schema `fpl3-local-v2`:

- `conda_executable`, `dev_prefix`, `workers.p1.prefix` and its timeout identify
  the manager and isolated interpreters.
- `import_dir`, `third_party`, `cache_dir`, `route_config` identify verified local
  inputs, component closure, cache and portable P1 parameters.

`configs/local.example.json` documents the placeholders. Actual machine and data
paths stay in ignored `workspace/`. Runtime does not use an old repository or
old environment as an execution engine.

The one-time importer has a separate `workspace/import.local.json`, with
`historical_run`, `historical_workspace`, `historical_repository`, `data_root`,
`survey_dir` and `dahia_dir`; see `configs/import.example.json`.

```powershell
.\scripts\fpl3.ps1 import-p1 --local workspace\import.local.json --out workspace\imports\p1-new --third-party workspace\third_party-new
```

This example requires new destinations. The completed canonical import remains
`workspace/imports/p1` with `workspace/third_party`. Import verifies source-image
hashes, manifests, protected-cohort metadata, pair order/roles and score attribution.
It copies reference artifacts and required component files; images remain in the
authorized read-only source. Dahia definitions were read as pinned Git blobs
because the original checkout was sparse; that checkout was not changed.

The original import and equivalent CLI import were exercised in Step 01. Redundant
and incomplete copies are covered by the migration cleanup record; the canonical
import and original receipts remain the evidence source.

## Actual-model checks and fresh P1

The original Conda migration exercised these command forms under v0.2. Their
output destinations now exist and retain that execution's code identity:

```powershell
.\scripts\fpl3.ps1 check-p1-numerics --local workspace\local.json --out workspace\review-conda-migration\p1-numerical-final.json
.\scripts\fpl3.ps1 run-p1 --local workspace\local.json --out workspace\runs\p1-conda-03 --fresh
.\scripts\fpl3.ps1 verify-migration --local workspace\local.json --run workspace\runs\p1-conda-03 --out workspace\review-conda-migration\parity-final
```

Choose new run/review destinations for later authorized executions. Run files and
reports refuse replacement. `--fresh` requires new extraction, as used here.
Without it, a matching validated cache can be reused after source hash and geometry
checks. The current cache is `workspace/cache-p1`; keys include worker numerical
identity, model/component hashes and executed package bytes.

The coordinator validates the frozen protocol under Python 3.13 and sends only
opaque image records and pairs through `fpl3-worker-v2` to the Python 3.10 worker.
Requests, responses, invocation arguments and source snapshots stay in the run.
Truth and subject selection are not worker inputs. JSON data and console logs
are separate. Missing or failed workers cause explicit infrastructure blocks.

`run-p1` returns the coordinator's authoritative `summary.json`; raw worker
accounting stays in `worker-summary.json`. Recorded pair outcomes remain intact
on late failure. A sealed directory may represent failure: `complete.json` alone
does not mean the run is eligible. `verify-migration` reports both `parity` and
`approved`, and exits with code 2 when approval fails even if arrays are exact.

For Step 01 closure, the original v2 run was rechecked without inference or source
artifact modification, using this command (its new output now exists):

```powershell
.\scripts\fpl3.ps1 verify-migration --local workspace\local.json --run workspace\runs\p1-conda-03 --out workspace\review-step01-closure\revalidation-final
```

It passed the existing-evidence checks with `verification_status=passed_legacy_evidence`.
The report explicitly retains the old format's missing worker-code and process-tree
attestations. New v3 runs require those records. See [closure details](step01-closure.md).

## Dahia access audit

The bounded Step 01 audit is complete and remains in `workspace/dahia-audit`,
`workspace/dahia-view-check` and `workspace/review-step01/dahia_artifacts.json`.
The equivalent current CLI form is:

```powershell
.\scripts\fpl3.ps1 dahia-check --source workspace\third_party\dahia --out workspace\dahia-audit-new --network
```

The network audit was not repeated merely to change the environment. It records
HTTP outcomes/hashes and distinguishes HTML from model archives. No Dahia weight
bytes were obtained, no TensorFlow profile was installed, and neither loading nor
inference was verified. A future authorized task requires accessible weights with
known provenance before compatible worker selection and synthetic checks. No new
Dahia route or two-pair smoke is authorized here.

## Step 02 supervisor evaluation

`supervisor-p1` has prepare, run and report phases. The historical `run-p1` and
`verify-migration` commands retain their original 100-image/250-pair purpose.
Use a separate private local configuration for the new cache; numerical route
parameters and existing Conda prefixes remain unchanged.

The private specification follows `configs/supervisor.example.json`. Its selected
evaluation metadata contains `cohort_sha256`, `sources` (path, SHA-256 and fields
read), and `records`. Each record carries string `subject_id`, `impression`,
anatomical `position`, `release`, `image_id`, `relative_path`, source `sha256`,
`width`, `height`, `source_ppi` and `processing_ppi`. The first source is the
original SD300B image catalog. Source geometry may be imported from recorded
original-input metadata; transformed images or scores are not calibration inputs.
The preparation verifies source metadata hashes and every selected anatomical
slot. It uses the imported cohort, never a new subject selection.

The following are command forms; substitute private files and new output names:

```powershell
.\scripts\fpl3.ps1 supervisor-p1 prepare --local workspace\supervisor.local.json --specification workspace\supervisor.specification.json --out workspace\supervisor-freeze-new
.\scripts\fpl3.ps1 supervisor-p1 run --local workspace\supervisor.local.json --prepared workspace\supervisor-freeze-new --role development --out workspace\runs\supervisor-dev-new
.\scripts\fpl3.ps1 supervisor-p1 run --local workspace\supervisor.local.json --prepared workspace\supervisor-freeze-new --role evaluation --development-run workspace\runs\supervisor-dev-new --out workspace\runs\supervisor-evaluation-new
.\scripts\fpl3.ps1 supervisor-p1 report --local workspace\supervisor.local.json --prepared workspace\supervisor-freeze-new --run workspace\runs\supervisor-evaluation-new --out workspace\supervisor-report-new
```

Preparation consumes the approved original P1 development evidence and the
Step 01 closure binding. It selects the lowest defined candidate boundary with
at most 2 false acceptances among all 200 development impostors, preserving ties.
It freezes that policy, route, components, numerical identity, code, both
manifests and primary demonstration IDs. Evaluation image access begins only
after this freeze and the new development protocol check. No sweep or threshold
adjustment on evaluation is supported.

The 50-subject evaluation uses 1,000 native source images, 2,000 independent
extractions (a/b per source) and 2,000 matcher comparisons. Four workers at most
process ten disjoint anatomical-finger partitions, each containing all subjects.
Every worker still uses CPU and four Torch threads. Partition logs capture both
output streams. The coordinator reassembles original pair order and records
source hashes/geometry before and after execution. Worker and wall timings are
reported separately; filtered views incur no additional matching.

The aggregate `approval.json` and ten v3 partition assessments govern use;
`complete.json` is only an inventory. Filesystem, source-binding, cache, process
or acknowledgement faults block approval. Explicit biometric processing failures
remain results and do not become threshold rejections. The new CLI exits with
code 2 if approval is denied, independently of match percentages. A report phase
rechecks original evidence without inference and exports Markdown, eligibility,
an opaque CSV and a validation receipt. The private review additionally contains
the verified Excel workbook and a local image demonstration; neither belongs in
public Git. See the [Step 02 report](step02-supervisor.md).
