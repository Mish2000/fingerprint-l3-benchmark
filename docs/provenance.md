# Component provenance and terms

## P1 is a composition

`ASM-F40-SIFT-SPATIAL` is the local composition also called P1: a learned Survey
detector, SIFT descriptions at predicted pore locations, and the spatial matcher
in the Dahia mirror. It is not an independent system authored by either paper's
authors. This project claims neither their reported accuracy nor a new algorithm.

| Layer | Source and treatment |
|---|---|
| Survey model, global NMS and architecture code | [Survey repository](https://github.com/azimIbragimov/Fingerprint-Pore-Detection-A-Survey), revision `47b128e55a540d84292f91e212ad1ce3789b2aec`; required files copied unchanged locally |
| SIFT helper and spatial matching | [Dahia mirror](https://github.com/xiaochengcike/high-res-fingerprint-recognition), revision `b3c46518f2fba4937902b5e56093177c01474de9`; `utils.py` and `matching.py` unchanged |
| P1 tiling, coordinate and helper integration | Transferred from the user's [earlier experiment](https://github.com/Mish2000/fingerprint-benchmark/tree/699bde574155a9d1aee37c7dd9f0301e3748e695/V2/experiments/l3_bridge_v1), reorganized into the new adapter |
| Contracts, strict importer, cache, CLI, reporting, Conda profiles/process boundary and synthetic tests | This project's engineering work |

The f40 checkpoint SHA-256 is
`3787e82d851701319c15fcd907d0e60df376aab2d7b8b9fe73003d2f41bffc99`.
It is a PyTorch state dictionary loaded by the upstream loader. Its local source,
revision and expected byte hash were checked before deserialization. Arbitrary
similarly named checkpoints are not accepted.

The local historical P1 files were compared with the **historical execution
revision**, not the current HEAD. Differences in those reference source files
were Windows line endings only. Import receipts retain both byte hashes. New
runs snapshot their actual Python source and configuration bytes. Historical
execution remains bound to those snapshots; publishing this repository does not
assign the earlier results to its new commits. The integration workflow is
documented in [CONTRIBUTING.md](../CONTRIBUTING.md).

The environment migration changed orchestration and dependency isolation, keeping
the P1 numerical adapter unchanged. The original venv run and new Conda runs each
retain their own source snapshots and environment identity. Development Python
3.13.15 and the Python 3.10.21 worker are identified separately in `fpl3-run-v2`.
Cleanup records hashes of removed redundant imports and superseded setup files;
canonical reference artifacts, original runs and Dahia HTTP evidence are retained.

## Separate terms

- Survey code: the local `LICENSE` was checked and copied with the closure. It
  states MIT and credits Azim Ibragimov (2022).
- Dahia code: the checked local license states **CC BY-NC-SA 4.0**, with credits
  to Gabriel Dahia Fernandes, Mauricio Pamplona Segundo and Universidade Federal
  da Bahia (2018). The mirror is identified as a mirror; authorship of the mirror
  itself has not been independently established.
- Weights: public links and repository licenses do not establish separate weight
  permissions. No distinct grant for the two unavailable Dahia payloads was
  located. The Survey checkpoint is distributed in its repository; no distinct
  checkpoint-specific grant was established beyond that repository's materials.
- Data: source dataset terms are separate from code and weights. This task does
  not create a redistribution permission or institutional authorization.
- Project code: no new blanket license has been assigned on the user's behalf.
  In particular, no MIT license is applied to the combined system.

Full license files stay beside the local third-party code. Private evidence,
templates, images, weights and per-pair scores are excluded from public source.
The review export contains only the report, aggregate summaries and opaque pair
comparison. No fingerprint screenshot is needed in the README.
