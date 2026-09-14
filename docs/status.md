# Candidate status

This is the single detailed candidate status table. Last verified **2026-09-14**.
Step 03 completed the bounded two-route comparison on the original twenty
development subjects; see its [report](step03-development.md) and
[filtered aggregate](evidence/step03-development.json). Both calibration profiles
preceded DEV-CHECK. The [Step 02 main P1 result](step02-supervisor.md) remains
unchanged. DP has not been evaluated on the fifty-subject main cohort. Private
manifests, source/point mappings, profiles, individual outcomes and the Hebrew
review package remain under `workspace/review-step03-development/` and its run.

The original Step 01 and Conda evidence remains unchanged. The
[closure review](step01-closure.md) preserves exact migration parity and the
explicit legacy-v2 attestation limitations; new evaluation partitions require
both-process source checks and quiescent worker trees. Development Conda Python
3.13.15 and P1 Conda Python 3.10.21 remain the settled environments.

| Candidate/component | Highest observed verification | Next-step condition |
|---|---|---|
| P1 / `ASM-F40-SIFT-SPATIAL` | Step 02: 50 subjects, 1,000 native SD300B images, 2,000 independently extracted a/b products and 2,000 validated pair outcomes; genuine ALL 282/500, next-subject FA ALL 50/500 at the frozen development threshold | Step 02 remains complete (X=500, Y=500); Step 03 adds a separately named development profile checked on ten other development subjects; no population FAR or superiority claim |
| Dahia CNN descriptor | README link and static model definition checked; three public access variants redirected to sign-in HTML; `file/d/.../view` returned HTTP 401; no model payload, checkpoint inspection, loading or inference | Obtain an accessible artifact with known provenance before selecting a compatible isolated worker |
| Dahia CNN detector | Same independently recorded access outcome; no model payload, checkpoint inspection, loading or inference | Same artifact requirement; a full-system smoke also requires a verified descriptor |
| Survey f40 + learned Dahia descriptor | Not implemented or tested | Descriptor artifact and synthetic worker checks remain prerequisites |
| `SYS-DAHIA-CNN-2018` full system | Source route inspected; not run | Both artifacts and their synthetic checks must succeed before the bounded two-pair smoke |
| `ASM-F40-DP32-SPATIAL` | Step 03: 10 DEV-CAL + 10 DEV-CHECK subjects, 400 native source images, 2,400 pair outcomes; DEV-CHECK genuine ALL 46/100, ring FA 0/100, extended FA 10/900 at its preselected calibration profile | Development comparison complete; stop for review before any main-cohort evaluation; no superiority or population FAR claim |
| PoreNet | Reserve candidate only; not implemented or run | Requires a future explicit research choice |

For each Dahia model, response sizes, hashes, final URLs and check times are
recorded separately. Those hashes describe HTML response bodies, **not weights**.
The access outcome does not prove that a weight does not exist. No TensorFlow
environment was created without a model payload. Neither full Dahia nor a
learned-descriptor-only composition is ready for the next comparison on this evidence.

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
- Step 01 closure had 65 tests; Step 02 had 83; Step 03 has 111. Coverage includes invalid
  acknowledgements, code mismatch/drift and real descendant termination. Ruff
  passed. Existing model-level synthetic evidence is preserved.

The whole-image versus tiled synthetic FCN check used the earlier geometry-test
tolerances (`atol=2e-6`, `rtol=2e-5`); observed max absolute difference was about
`3.16e-6`. That combined tolerance passed, and repeated tiled inference was
exact. It did not change the migration policy: migration demanded exact array
and score equality and obtained it.
