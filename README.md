# fingerprint-l3-benchmark

[![CI](https://github.com/Mish2000/fingerprint-l3-benchmark/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Mish2000/fingerprint-l3-benchmark/actions/workflows/ci.yml)

Research infrastructure for comparing fingerprint verification routes that use
**Level-3 information with learned pore detection**, on source images of at least 1000 PPI. A route
produces a raw similarity score or an explicit failure from two images.

```text
Two native gray8 images (1000 PPI)
  → Survey FCN f40 → stitched heatmap → global NMS → predicted pore points
  → SIFT descriptions at those points → spatial matching → score / failure
```

## Current verified state

Development uses **Miniconda with Python 3.13.15**. P1 runs in a separate Conda
worker with Python 3.10.21 and its historical numerical dependencies. A versioned
JSON process interface lets the main project and model environments evolve
separately. The [environment policy](docs/environment-policy.md) explains the
version choice, exact package locks and upgrade procedure.

On **2026-09-13**, fresh P1 execution through the Conda environments reproduced
all **133,502 points, 100 descriptor arrays and 250 scores/statuses exactly**,
including three valid zeros. The same 100 development images and 250 pairs were
used; all features were extracted anew. **42 synthetic tests**, Ruff checks and
separate actual-model geometry checks passed.

The Dahia CNN detector and descriptor remain **access-blocked**: their public
endpoints returned sign-in HTML or HTTP 401. Neither weight was obtained, loaded
or run. See the single detailed [candidate status](docs/status.md), the original
`workspace/review-step01/` evidence and the current
`workspace/review-conda-migration/readout_he.md`. These detailed research records
remain private; [candidate status](docs/status.md) provides the public aggregate
results. Source publication preserves the original execution snapshots and does
not reassign those historical runs to a new commit.

## Quickstart

Windows x86-64 with Miniconda installed. Run from the project root:

```powershell
.\scripts\bootstrap.ps1
.\scripts\test.ps1
.\scripts\fpl3.ps1 doctor
```

Bootstrap creates `.conda/dev` and `.conda/p1` from the checked Windows locks and
installs this package into both. It discovers the existing Miniconda installation;
use `-CondaExe 'path\to\conda.exe'` if needed. The wrappers activate the selected
environment through `conda run`; manual shell activation is optional.

Default tests need no private dataset, model or network. Real P1 execution also
requires authorized data, verified component artifacts and local path settings.
[Execution instructions](docs/running.md) cover that configuration, both-environment
diagnostics, fresh inference, parity verification and the bounded Dahia audit.

Pull requests and updates to `main` run whitespace checks and the synthetic suite
with Ruff on Windows, recreating the development environment from its exact lock.
CI checks source integration; historical model and migration evidence remains
local. See the [integration workflow](CONTRIBUTING.md) for contribution policy.

## Project map

| Location | Purpose |
|---|---|
| `src/fpl3/` | Protocol, contracts, coordinator, model worker and verification |
| `tests/` | Synthetic contracts, population, cache, component-swap and process tests |
| `configs/` | Portable P1 parameters and local configuration examples |
| `environments/` | Conda profile declarations and Windows package locks |
| `scripts/` | PowerShell bootstrap, CLI and test entry points |
| `docs/` | Environment policy, architecture, research context and provenance |
| `workspace/` | Ignored local imports, models, caches, runs and review evidence |
| `CONTRIBUTING.md` | Commit, review, integration and publication policy |

## Scope and attribution

P1 combines a learned [Survey detector](https://github.com/azimIbragimov/Fingerprint-Pore-Detection-A-Survey)
with SIFT and spatial matching from the identified
[Dahia mirror](https://github.com/xiaochengcike/high-res-fingerprint-recognition).
The engineering contribution is the independent composition, explicit contracts,
environment separation, provenance and migration verification. It builds on the
user's earlier P1 experiment and does not claim a new biometric algorithm.

Migration results do not establish biometric accuracy, comparative superiority
or anatomical confirmation of predicted pores. SD300 contains scanned ink cards;
SD300B/C are related scans. Protected-cohort images and scores were not opened,
and historical exposure records were retained. Step 01 and the environment
migration are complete; new research routes remain outside this task.

Code, weights and data have separate terms. Survey code carries MIT; the Dahia
mirror carries CC BY-NC-SA 4.0. No blanket license was assigned to this combined
project. [Provenance and terms](docs/provenance.md) records attribution and unresolved
weight permissions. Research images, templates, weights, individual scores and
machine settings remain local and ignored.
