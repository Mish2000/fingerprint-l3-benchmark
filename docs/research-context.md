# Research context and boundaries

The Conda migration changed execution infrastructure only. Step 02 adds the fixed
supervisor reporting protocol on P1 and the existing 50-subject SD300B cohort,
while preserving historical development and migration evidence. Interpreter
decisions live in [environment policy](environment-policy.md); current verified
outcomes live in [status](status.md).

The intended comparison unit is two images through processing, feature
extraction and matching to a numeric score or an explicit failure. It is a
research comparison of routes that use Level-3 information and learned models.
It is not a production identification system, liveness test, universal threshold
or calibrated probability service.

Source resolution describes the original image sampling. Processing resolution
describes the pixels presented to a component. Resizing a lower-resolution image
does not create native Level-3 information. At least 1000 PPI is the project's
source eligibility requirement for resolving fine detail; meeting it alone does
not prove that a route uses pores or that a detected mark is an anatomical pore.
P1 uses a learned f40 detector, then local texture descriptions at the predicted
locations and geometric consistency in matching. Those locations remain model
predictions, not anatomically validated annotations.

P1 is a composition of existing components. A complete external system should
be identified separately from such a composition and from a modified variant.
A patch with a fixed pixel width has different physical support at different
PPI; descriptor changes across resolutions cannot be treated as equivalent by
pixel dimensions alone.

SD300 consists of scanned ink fingerprint cards. Image artifacts, scanner
properties and ink marks limit anatomical interpretation and generalization.
SD300B and SD300C are related scans of the same cards, not independent subject
populations. SD300C header/resolution anomalies remain a later ingestion concern;
Neither Step 01 nor Step 02 opens or implements its image route.

The fixed development sample has five subjects, ten fingers per subject, and
one PLAIN plus one ROLL image per finger: 100 images and 250 directed pairs.
PLAIN FRGP 11 maps to the right thumb and 12 to the left thumb. Multi-finger
images are excluded. Pairs are validated from anatomical metadata, never by
filename string substitution.

The existing 50-subject cohort was metadata-only in Step 01. Step 02 authorizes
its SD300B P1 evaluation after freezing the development threshold, route, code
and protocol, and completing the new-protocol development check. It remains
evaluation data, with no training or threshold/model tuning on those subjects.
The five development and fifty evaluation subjects do not overlap. The old
experiment's known exposure record is retained privately, including prior
exposure within that protected cohort; moving repositories does not reset it.
No protected images or scores were opened in Step 01.

Synthetic geometry tests establish implementation behavior. A two-pair smoke
would establish that a chain runs. Exact migration establishes preservation of
the earlier experiment. None of these establishes biometric accuracy, advantage
over another method, SOTA performance or generalization to another population.
Step 02 reports all 500 genuine pairs and a SELF-eligible view of those same
scores. It reports the 500 cyclic next-subject, same-finger negatives both ALL
and with both units SELF-eligible, without rebuilding the ring. Two independent
extractions of the same source support SELF, not independence of acquisitions.
The threshold is the lowest defined unique-score/above-maximum candidate meeting
FA <= 2 on the 200 original development impostors. This is experimental policy
fitting, not a population risk guarantee. No evaluation threshold sweep, training,
P2 repair, SD300C run, DP/PoreNet or further population expansion is authorized.
