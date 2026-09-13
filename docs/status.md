# Candidate status

This is the single detailed candidate status table. Last verified **2026-09-13**.
Current P1 revalidation: `workspace/review-step01-closure/revalidation-final/migration_summary.json`
and the Hebrew closure readout. The original Step 01 and Conda evidence,
including `workspace/review-step01/dahia_artifacts.json`, remains unchanged.
The public [aggregate evidence](evidence/migration-summary.json) is a filtered
copy of the final migration summary, bound to the original record by SHA-256.
It contains no subject identities, image paths or individual scores. Detailed
records remain private, and historical runs retain their original source binding.
The [closure review](step01-closure.md) separates numerical parity from approval.
The existing run passed the legacy evidence checks without new inference. Worker
code checks from before/after that original execution were not recorded; this
limitation is preserved instead of inferred from package versions.
Development now uses Conda Python 3.13.15 and a separate Conda Python 3.10.21 P1
worker; [environment policy](environment-policy.md) is the settled standard.

| Candidate/component | Highest observed verification | Next-step condition |
|---|---|---|
| P1 / `ASM-F40-SIFT-SPATIAL` | 100 SD300B images and 250 successful pairs with exact arrays, mappings, statuses and scores; original run revalidated read-only with coherent acknowledgements and counts | Step 01 closure complete; legacy worker-code attestation remains explicitly unrecorded; no accuracy or superiority claim |
| Dahia CNN descriptor | README link and static model definition checked; three public access variants redirected to sign-in HTML; `file/d/.../view` returned HTTP 401; no model payload, checkpoint inspection, loading or inference | Obtain an accessible artifact with known provenance before selecting a compatible isolated worker |
| Dahia CNN detector | Same independently recorded access outcome; no model payload, checkpoint inspection, loading or inference | Same artifact requirement; a full-system smoke also requires a verified descriptor |
| Survey f40 + learned Dahia descriptor | Not implemented or tested | Descriptor artifact and synthetic worker checks remain prerequisites |
| `SYS-DAHIA-CNN-2018` full system | Source route inspected; not run | Both artifacts and their synthetic checks must succeed before the bounded two-pair smoke |
| DP / PoreNet | Reserve candidates only | A future explicit research choice; no implementation started |

For each Dahia model, response sizes, hashes, final URLs and check times are
recorded separately. Those hashes describe HTML response bodies, **not weights**.
The access outcome does not prove that a weight does not exist. No TensorFlow
environment was created without a model payload. Neither full Dahia nor a
descriptor-only composition is ready for the next comparison on this evidence.

## Migration evidence

- 5 development subjects; 100 images; 50 genuine and 200 directed impostor pairs.
- Source SHA-256 checks passed for all 100 permitted inputs; no staging copies.
- 133,502 source/retained points, preserving order and native coordinates.
- 100/100 exact descriptor arrays and source-index mappings.
- 250/250 exact statuses and raw scores; three zeros preserved; no failures.
- Maximum absolute and relative numeric differences: zero. Per-image numeric
  details, including dtype/shape and relative differences, are retained locally.
- CPU, four Torch threads, Python 3.10.21 and the historical numerical package
  versions. Fresh extraction for all images; zero reference-cache reuse.
- Default tests: 65 passed, including early/partial/late process failures, invalid
  acknowledgements, code mismatch/drift and real descendant termination. Ruff
  passed. Existing model-level synthetic evidence is preserved.

The whole-image versus tiled synthetic FCN check used the earlier geometry-test
tolerances (`atol=2e-6`, `rtol=2e-5`); observed max absolute difference was about
`3.16e-6`. That combined tolerance passed, and repeated tiled inference was
exact. It did not change the migration policy: migration demanded exact array
and score equality and obtained it.
