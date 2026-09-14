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

The Step 01 closure correction changes finalization, process containment and
verification only. The numerical adapters and original scientific artifacts are
unchanged. New verification identifies the exact original run and the verifier's
own file hashes separately. The supplied review probe reproduced the late-failure
defect; regression tests assert the corrected approval contract, without preserving
the defective behavior. Legacy missing code attestations remain explicit in the
[closure report](step01-closure.md).

Step 02 uses the earlier project's anatomical pair-generation and SELF-filtering
logic as reference material, read locally at the supplied source revision
`fd3e9b1a50c47e182ece70c991204c9246ce65fc`. The new implementation creates cyclic
next-subject/same-finger negatives, with new pair identities, instead of the old
same-subject/finger-shift experiment. The old package is not an execution engine.
The supplied replacement specification distinguishes reported supervisor messages
from the user's/current implementation decisions. It does not establish supervisor
endorsement of the local P1 composition. The Windows path correction changes
filesystem handling at the adapter boundary without changing numerical processing.

## Separate terms

Step 03 adds a DP32 adapter derived from `dp_descriptors` and
`compute_orientation` in the same pinned Dahia `utils.py` at
`b3c46518f2fba4937902b5e56093177c01474de9`. Its attribution and CC BY-NC-SA 4.0
terms apply to the derived operations in `direct_pore.py`.
The original [copyright and license notice](../licenses/dahia-dp32.txt) is retained
for these derived operations; it does not assign a blanket project license.
Local changes expose point-to-descriptor mappings and invalid-point reasons, validate integral
coordinates, precompute the unchanged circular mask, and evaluate orientation
only where its original Gaussian support is consumed. The original point-border
inequalities, patch size 32, input float32 [0,1], Sobel and reduction order,
Gaussian filtering, affine rotation and normalization are preserved. Finite
outputs were compared with zero numerical tolerance against the original code;
the original zero-norm NaN becomes an explicit per-point exclusion.

`ASM-F40-DP32-SPATIAL` is a local composition using Survey's learned detector,
this classical descriptor and Dahia's unchanged spatial matcher. It is not the
complete external DP system and does not inherit paper accuracy claims. It
requires neither the blocked Dahia weights nor TensorFlow. SIFT's historical
median/CLAHE preparation is not added to DP. Known-angle SIFT diagnostics remain
synthetic controls and are not an additional experimental fingerprint route.

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
Public exports contain filtered aggregate summaries only. The separately labeled
private review ZIP additionally contains the opaque individual pair table, with
no images, templates or weights. The local HTML demonstration remains private.
No fingerprint screenshot is included in the README.
