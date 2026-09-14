# fingerprint-l3-benchmark

[![CI](https://github.com/Mish2000/fingerprint-l3-benchmark/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Mish2000/fingerprint-l3-benchmark/actions/workflows/ci.yml)

Research infrastructure for comparing fingerprint verification routes that use
**Level-3 information with learned pore detection**, on source images of at least 1000 PPI. A route
produces a raw similarity score or an explicit failure from two images.

```text
Two native gray8 images (1000 PPI)
  → Survey FCN f40 → stitched heatmap → global NMS → predicted pore points
  → SIFT or DP32 descriptions at those points → spatial matching → score / failure
```

## Current verified state

Step 03 is complete: **20 original development subjects, 400 native SD300B
images and 4,800 unique comparisons** across P1 and a DP32 composition. The
original first ten subjects calibrated the two profiles; the last ten checked
those fixed profiles. Both profiles were sealed before DEV-CHECK started.

| Route | DEV-CHECK genuine ALL | Ring false acceptances | Extended false acceptances |
|---|---:|---:|---:|
| P1 / SIFT | 64/100 | 1/100 | 28/900 |
| DP32 composition | 46/100 | 0/100 | 10/900 |

The [development report](docs/step03-development.md) includes calibration,
SELF-filtered denominators, component checks and limitations. These are fixed
development sample results, not population FAR or a ranking by genuine acceptance
alone. The 100 ring negatives reference the same outcomes among the 900 extended
negatives; filtered views add no matcher calls.

The [Step 02 main result](docs/step02-supervisor.md) remains **282/500 genuine
matches and 50/500 false acceptances** at its original threshold. Step 03 did not
run DP or apply new thresholds on the main fifty-subject cohort.

**111 synthetic tests and Ruff passed.** Development Conda Python 3.13.15 and
the separate P1 Python 3.10.21 numerical environment are unchanged. New runs
require source checks, acknowledgements and confirmed process-tree termination.
See [environment policy](docs/environment-policy.md), the [Step 01 closure](docs/step01-closure.md)
and the single [candidate table](docs/status.md).

Images, templates, weights, individual scores and detailed Hebrew review packages
remain private under ignored `workspace/`. Public documentation contains filtered
aggregates. Local operational notes are excluded from publication.

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
| `configs/` | Fixed P1/DP32 parameters and portable configuration examples |
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
The DP32 composition adds the mirror's classical Direct Pore descriptor
with recorded point filtering and verified source equivalence.

Migration results do not establish biometric accuracy, comparative superiority
or anatomical confirmation of predicted pores. SD300 contains scanned ink cards;
SD300B/C are related scans. Step 02 evaluated only the explicitly authorized
fixed SD300B cohort after freezing its development decision policy. Historical
exposure remains recorded. Step 03 stopped after its two development groups. Further evaluation, training
and resolutions require a new research decision.

Code, weights and data have separate terms. Survey code carries MIT; the Dahia
mirror carries CC BY-NC-SA 4.0. No blanket license was assigned to this combined
project. [Provenance and terms](docs/provenance.md) records attribution and unresolved
weight permissions. Research images, templates, weights, individual scores and
machine settings remain local and ignored.
