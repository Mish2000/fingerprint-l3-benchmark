# Step 03 development comparison

Two fixed compositions were completed on the original twenty selected
development subjects: the first ten form DEV-CAL and the last ten DEV-CHECK.
The original five are at the start of DEV-CAL. There is no overlap with the main
fifty-subject cohort. The experiment used 400 native SD300B images at 1000 PPI
and 4,800 unique route/pair outcomes. All forty worker partitions passed approval.

P1 remains Survey f40 → SIFT → spatial. The second route is the local composition
Survey f40 → Direct Pore DP32 → the same spatial matcher. The f40 detector is
learned; both descriptors and the matcher are classical. This is not the
complete original DP system, and predictions are not anatomically verified pores.

Each route's new development profile was selected only from DEV-CAL's 900 directed
same-finger impostor attempts. The budget is floor(score-bearing count / 100),
without filtering calibration negatives by SELF. The smallest unique score or
boundary above the maximum satisfying that budget is used with `score >= threshold`.
Both profiles were saved and sealed before any DEV-CHECK score computation or
reading. Genuine and SELF scores did not select the thresholds.

| Group | Route | New development threshold | Genuine ALL matches | Ring ALL false acceptances | Extended ALL false acceptances |
|---|---|---:|---:|---:|---:|
| DEV-CAL | P1 / SIFT | 2.695395178305679 | 43/100 | 2/100 | 9/900 |
| DEV-CAL | DP32 composition | 1.0898890514099095 | 22/100 | 0/100 | 9/900 |
| DEV-CHECK | P1 / SIFT | 2.695395178305679 | 64/100 | 1/100 | 28/900 |
| DEV-CHECK | DP32 composition | 1.0898890514099095 | 46/100 | 0/100 | 10/900 |

The extended 900 comparisons include the 100 ring pairs by explicit IDs;
they are not another 100 matcher calls. Each route/group has 200 SELF pairs,
100 genuine pairs and 900 unique impostors. There are no comparisons across the
two development groups. Match/processing-failure counts and SELF-filtered
denominators are retained in the [public aggregate](evidence/step03-development.json).
The full six-section Hebrew reports and opaque individual outcomes remain private.

| Group | Route | PLAIN SELF | ROLL SELF | X | Y | Genuine SELF-FILTERED | Ring SELF-FILTERED false acceptances |
|---|---|---:|---:|---:|---:|---:|---:|
| DEV-CAL | P1 / SIFT | 100/100 | 100/100 | 100 | 100 | 43/100 | 2/100 |
| DEV-CAL | DP32 composition | 100/100 | 100/100 | 100 | 100 | 22/100 | 0/100 |
| DEV-CHECK | P1 / SIFT | 100/100 | 100/100 | 100 | 100 | 64/100 | 1/100 |
| DEV-CHECK | DP32 composition | 100/100 | 100/100 | 100 | 100 | 46/100 | 0/100 |

Filtering depends only on both SELF decisions for the particular route/profile.
It never removes a genuine failure from ALL, reorders subjects or selects a new
neighbor. Explicit processing failures remain separate from score rejections.
Rates on a zero denominator are undefined.

## Component and execution checks

DP uses source-style float32 [0,1] pixels, Gaussian filtering, original orientation
normalization and a fixed 32×32 window. It does not inherit SIFT's median/CLAHE.
Patch size 32 was a prior operating choice, not a parameter proven optimal for
SD300. Integral coordinates, the original asymmetric border rule and retained
source indices are checked. Zero-norm or nonfinite descriptors are explicitly
excluded per point, without invented zero descriptors.

The local orientation optimization computes the original reductions only where
their Gaussian support is consumed. Zero tolerance was declared before research
scores. Finite descriptor arrays and consumed orientations matched the original
source exactly on rectangular synthetic fixtures and the first fixed DEV-CAL
source. On that source, description took about 0.34 seconds versus 18.7 seconds
for the original full computation; this is a local measurement, not a general
speed guarantee.

The supplied SIFT probe ran in the existing OpenCV 3.4.18 worker: 81 correct
correspondences at 0°, 76 at 10°, 11 at 20°, and zero at 30°/45°/90°. The known-angle
control is a synthetic diagnostic only. DP's separate integer-geometry fixture
retained 96 common descriptors from 108 points, with 96/47/0 correct
correspondences at 0°/90°/180° and no incorrect retained correspondences. Border
filtering and orientation effects are reported separately. Neither probe
quantifies the cause of errors between real PLAIN and ROLL acquisitions.

The two routes shared all 800 independent a/b f40 products: 200 came from the
approved historical five-subject run, and 600 were newly detected. SIFT reused
the corresponding 200 historical descriptor products and computed 600 new ones;
DP computed 800 new descriptor products. Each reuse was bound to image bytes,
replica, components, numerical environment and settings. Per-route descriptor
retention is exposed, and historical scores were not reused.

111 synthetic tests and Ruff passed. All forty partitions retained the existing
v3 source, acknowledgement and process-tree checks. The original 250 overlapping
Step 01 scores and 200 overlapping Step 02 development outcomes matched exactly
when recomputed; the two comparison sets overlap each other. The old runs remain
bound to their own executed source snapshots.

All 21,473 inventoried historical files remained unchanged. Run wall time, including execution coordination and validation, was 89.73 minutes. Worker/component times are summed separately and are not wall-time additions.
The existing two Conda profiles were preserved numerically; only project package
metadata changed to 0.5.0. Dahia model weights remain blocked and TensorFlow was
not installed.

## Historical result and stopping point

The [Step 02 main result](step02-supervisor.md) remains 282/500 genuine matches
and 50/500 ring false acceptances, with both SELF populations at 500/500, using
the original threshold. Step 03's P1 profile has a different name and does not
replace that policy. Neither new threshold was applied to the fifty-subject
cohort. DP has not been evaluated on that main cohort.

Do not rank routes using genuine acceptance alone when their false acceptance
rates differ. A 1% calibration target is not a guarantee for another group.
Shared subjects/images create dependent observations, historical exposure is
retained, and scanned ink cards limit generalization. These are development
samples, not a population FAR estimate or final generalization evaluation.

The experiment stops after DEV-CHECK. Training, parameter sweeps, another matcher,
another dataset/resolution and further main-cohort evaluation require a new
research decision. See [attribution and separate terms](provenance.md).
