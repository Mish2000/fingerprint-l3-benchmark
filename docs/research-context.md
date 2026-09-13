# Research context and boundaries

The Conda migration changes execution infrastructure only. The frozen protocol,
source-resolution rules and research limits below remain in force. Interpreter
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
Step 01 does not open or implement its image route.

The fixed development sample has five subjects, ten fingers per subject, and
one PLAIN plus one ROLL image per finger: 100 images and 250 directed pairs.
PLAIN FRGP 11 maps to the right thumb and 12 to the left thumb. Multi-finger
images are excluded. Pairs are validated from anatomical metadata, never by
filename string substitution.

The protected 50-subject cohort is checked using metadata only. The old
experiment's known exposure record is retained privately, including prior
exposure within that protected cohort; moving repositories does not reset it.
No protected images or scores are opened in Step 01.

Synthetic geometry tests establish implementation behavior. A two-pair smoke
would establish that a chain runs. Exact migration establishes preservation of
the earlier experiment. None of these establishes biometric accuracy, advantage
over another method, SOTA performance or generalization to another population.
No score-based pair filtering, threshold search, training, P2 repair, SD300C run,
DP/PoreNet integration or expanded benchmark is authorized in this step.
