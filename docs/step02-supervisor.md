# Step 02: supervisor protocol for P1

The fixed P1 composition was evaluated on the existing **50-subject SD300B
cohort: 500 PLAIN and 500 ROLL native 1000-PPI images**. All **2,000 planned
comparisons** have validated outcomes. Ten v3 partition runs and the aggregate
passed evidence checks. Completion does not depend on a match percentage.

The decision rule, selected before evaluation, is
**score >= 1.8128025490006117**. Selection used only
the 200 approved original development impostor scores, with 2/200
false acceptances. It chose the smallest of the unique-score candidates plus a
boundary above the maximum that satisfied FA <= 2. Ties stay together. This is
development fitting of decision policy on a small, previously used sample, not a
guarantee of 1% population FAR. Genuine, SELF and evaluation scores did not select
the threshold. Detector 0.65 and descriptor ratio 0.7 are different parameters.

## Six-section readout

1. Inputs: **500 PLAIN + 500 ROLL**; all source hashes, original dimensions,
   identities and anatomical slots verified before/after execution.
2. PLAIN SELF: first row below, with independent extraction of both sides.
3. ROLL SELF: second row below, with independent extraction of both sides.
4. Metadata joins: **500** genuine anatomical units; **X=500** survive
   both SELF checks. A metadata join is not a successful biometric comparison.
5. Genuine PLAIN/ROLL: ALL and SELF-FILTERED below.
6. Next-subject PLAIN/ROLL, same anatomical finger: ALL and SELF-FILTERED below,
   with **Y=500** retained negative pairs.

| Population | View | Matches / false accepts | Non-matches | Processing failures | Denominator | Match / FA rate |
|---|---|---:|---:|---:|---:|---:|
| plain_self | ALL | 500 | 0 | 0 | 500 | 100.00% |
| roll_self | ALL | 500 | 0 | 0 | 500 | 100.00% |
| plain_roll_mated | ALL | 282 | 218 | 0 | 500 | 56.40% |
| plain_roll_mated | SELF_FILTERED | 282 | 218 | 0 | 500 | 56.40% |
| plain_roll_next_subject_non_mated | ALL | 50 | 450 | 0 | 500 | 10.00% |
| plain_roll_next_subject_non_mated | SELF_FILTERED | 50 | 450 | 0 | 500 | 10.00% |


Both SELF populations matched all 500 inputs, so no units were removed:
X=Y=500 and ALL/SELF-FILTERED coincide. The evaluation's observed **10.00%**
next-subject false acceptance rate exceeds the **1.00%** development selection
rate. The original threshold was retained; these are the measured results at
that fixed policy, not a new threshold search or a population FAR estimate.

For each rate, the numerator is the matches/false-accepts column and the
denominator is shown explicitly. A processing failure is distinct from a
threshold rejection. A zero filtered denominator would give an undefined rate.
The unfiltered genuine result is the primary comparison measure; filtered results
are a conditional view and do not replace it.

## Protocol and source distinctions

The ordered, pre-existing cohort was not reselected. PLAIN codes 11/12 map to
anatomical fingers 1/6, with other single-finger positions unchanged. Multi-finger
codes 13/14 are excluded. Each negative pairs the current subject's PLAIN with
the next list subject's ROLL at the same anatomical position; the last wraps to
the first. These are 500 fixed negatives, not all-against-all or finger-shift.
Protocol/pair IDs are new. Historical finger-shift results retain their meaning
and were not relabeled or rerun.

The supplied specification attributes the six-section structure and SELF cleanup
to supervisor messages, next-subject wording to Michael's report and the user's
clarification, and cyclic wraparound, threshold selection and filtered-view edge
handling to current implementation decisions. Those source distinctions are
preserved; the original WhatsApp archive was not independently reread here.
Conforming to this report structure does not imply supervisor endorsement of the
P1 composition.

Each source has **two independently invoked extractions**, totaling 2,000. Side a
is reused for genuine/negative comparisons, with no new extraction for each pair.
SELF uses the real spatial matcher on sides a/b. Eligibility is the conjunction
of PLAIN SELF and ROLL SELF decisions. Genuine non-matches never cause filtering.
Both units of a negative must be eligible; the fixed subject ring is never rebuilt
to find a surviving replacement. ALL/FILTERED add no matching calls.

## Validation and timing

**83 synthetic tests and Ruff passed**. Coverage includes nonconsecutive subject
IDs and cyclic boundaries, thumb/missing/duplicate input cases, ties, zero and
float64 maximum threshold boundaries, genuine failure surviving SELF filtering,
single-side SELF failure, empty views, real independent extraction calls and
infrastructure rejection. Existing acknowledgement, code drift and bounded
process-tree regressions remain in the suite.

The new development protocol completed 200 comparisons on the original five
subjects. All 200 fresh a/b template-array comparisons against the approved
100-image original were exact; all 100 overlapping genuine/next-subject scores
recomputed exactly. Development is validation and threshold data, not the main
evaluation. The two populations have no subject overlap.

A development-only run exposed an extended Windows path/separator defect. Its
aggregate was rejected by existing path-binding checks and is preserved. The
fix resolves a run directory after creating it, uses the native separator at the
Survey output writer, and classifies filesystem/cache/source-binding errors as
infrastructure failures. Numerical settings and the chosen decision remained
unchanged; evaluation images had not been opened when this was corrected.

Evaluation wall time was **59.14 minutes**,
using at most four independent workers, each with four CPU Torch threads.
Cumulative detection/description time was
5778.189/62.416 seconds.
Cumulative SELF matching was
6528.462 seconds;
genuine/negative matching was
11.931/11.157 seconds.
Cumulative worker time overlaps across parallel processes. The
[filtered aggregate evidence](evidence/step02-supervisor.json) provides the
separate input, model-load, overhead and per-population timings.

## Evidence and limits

The actual executed source files, frozen manifests/decision, native input hashes,
independent template arrays/mappings, opaque pair outcomes, worker exchanges and
Windows Job quiescence are retained privately. The Hebrew Markdown and Excel
reports, a local demonstration and a small private review ZIP accompany them.
Primary demonstration pairs were chosen before evaluation by manifest order;
additional first non-matches/failures follow a recorded rule.

All 1,641 historical evidence files inventoried at task start
remain unchanged. [Step 01](step01-closure.md) remains closed, including its
explicit legacy-v2 attestation limits. New evaluation evidence is bound to its own
executed bytes, not retroactively assigned to an unrelated commit.

P1 is a local composition of Survey f40, SIFT and spatial matching. Only pore
prediction is learned; no anatomical pore-ground-truth claim is made. SD300B
contains scanned ink cards. B/C are related scans, and C was not evaluated.
Historical exposure records remain visible privately; evaluation is not claimed
to be never seen. The results do not establish population FAR, independent
comparisons, generalization to live sensors or superiority over another route.
No training, retuning on the 50, DP, P2, other method or resolution was started.
Code, model and dataset terms remain separate; no blanket license was added.
