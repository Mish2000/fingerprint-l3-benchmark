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

Step 02 is complete: **50 existing evaluation subjects, 1,000 native SD300B
images and 2,000 P1 comparisons** passed evidence validation. The fixed decision
rule was selected beforehand from the 200 approved development impostor scores.
The [six-section supervisor report](docs/step02-supervisor.md) presents SELF,
metadata joins, genuine matching and cyclic next-subject matching, each with its
required ALL/SELF-FILTERED view and explicit denominator.

At that fixed threshold, genuine ALL matched **282/500**,
and next-subject ALL produced **50/500 false acceptances**.
The report separates these results from processing failures, development data
and population-risk claims. It distinguishes supervisor-source statements from
current implementation choices.

Development uses Conda Python **3.13.15**; P1 uses a separate Conda Python
**3.10.21** worker with unchanged numerical dependencies, CPU and four Torch
threads. New runs require before/after source checks, complete acknowledgements,
validated outputs and confirmed process-tree termination. **83 synthetic tests
and Ruff passed.** See [environment policy](docs/environment-policy.md).

[Step 01 closure](docs/step01-closure.md) remains intact, including exact
100-image/250-pair migration parity and the original v2 attestation limitations.
Its scientific snapshots were preserved. Dahia weights remain access-blocked;
DP/PoreNet and P2 were not started. The single detailed
[candidate table](docs/status.md) records current verification.

Research images, templates, models, individual scores and the detailed Hebrew
review remain private under ignored `workspace/`. Public reports are filtered
aggregates. Local `AGENTS.md` provides current agent context and is intentionally
excluded from publication.

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
SD300B/C are related scans. Step 02 evaluated only the explicitly authorized
fixed SD300B cohort after freezing its development decision policy. Historical
exposure remains recorded. Further methods, training and resolutions remain
outside this completed task.

Code, weights and data have separate terms. Survey code carries MIT; the Dahia
mirror carries CC BY-NC-SA 4.0. No blanket license was assigned to this combined
project. [Provenance and terms](docs/provenance.md) records attribution and unresolved
weight permissions. Research images, templates, weights, individual scores and
machine settings remain local and ignored.
