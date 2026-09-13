# Environment definitions

The project develops on Miniconda CPython 3.13.15 and executes historical P1 in a
separate CPython 3.10.21 worker. See [policy](../docs/environment-policy.md) and
[commands](../docs/running.md).

| File | Role |
|---|---|
| `dev.yml` | Intended native development dependencies, ordinary `cp313` build |
| `p1.yml` | Intended native P1 interpreter and packaging tools |
| `locks/dev-win-64.explicit.txt` | Exact tested native development builds and checksums |
| `locks/p1-win-64.explicit.txt` | Exact tested native P1 builds and checksums |
| `locks/p1-pip.txt` | Pinned pip-owned worker dependencies, installed with `--no-deps` |

`scripts/bootstrap.ps1` recreates both profiles using the Windows locks, installs
the pip-only worker dependencies and installs this repository separately into both
prefixes. YAML files describe native solver inputs; installing `p1.yml` alone is
not the full P1 setup. Use conda-forge with strict channel priority when resolving
new locks. Do not merge legacy numerical packages into the development profile.

Locks contain package URLs, not local interpreter paths. Private doctor reports
and Conda/pip inventories identify actual installed prefixes. New platforms or
interpreter targets require their own tested lock and route verification.
Historical inventories remain with their original run evidence.
