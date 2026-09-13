# Step 01 closure: run evidence and numerical parity

The supplied review of `c52d95e383232682eac7607c2967b2a56344a39f` identified a
completion-contract defect. A worker could publish all arrays, pairs and its
summary, then lose its final acknowledgement. The coordinator returned blocked
counts while retaining a successful summary, and the verifier reported exact
parity without rejecting the unresolved process failure.

The original probe reproduced this locally using synthetic data. Its five source
files were matched to the reviewed Git blobs; the local historical snapshots
differed only in the recorded CRLF/LF normalization. No trained model or source
fingerprint was used in the failure probe.

## Correction in v0.3.0

- `summary.json` is the coordinator's authoritative run state and is returned
  unchanged by the CLI. The worker's original accounting is retained separately
  in `worker-summary.json`, together with every pair/image output.
- Numerical outcomes and infrastructure state are separate. Late failure can
  leave successful observed pairs and exact diagnostic arrays while the run is
  `infrastructure_failure`. Unrecorded pairs remain explicit, and an unconfirmed
  physical matcher-call count is null.
- `complete.json` seals a file collection, including failed-run evidence. Overall
  migration approval also requires consistent coordinator/worker completion,
  acknowledgement and source bindings, valid coverage and fresh extraction.
  `verify-migration` exits with code 2 if `approved=false`, even when `parity=exact`.
- The Windows launcher assigns a gated process to a Job Object before releasing
  it to start Conda. Timeout and unexpected live descendants are terminated;
  sealing requires confirmed process-tree quiescence. Failure to establish that
  condition leaves the run unsealed.
- Both processes check fpl3 source hashes and loaded module locations before and
  after execution. Worker requests, replies and the run snapshot must agree.
  Code mismatch or drift blocks approval. No identity is inferred from Python
  or dependency versions alone, and no historical run is rebound to current HEAD.

This changes the existing run contract without adding a general recovery engine,
altering numerical adapters, changing environments or starting another candidate.

## Validation

**65 synthetic tests and Ruff passed locally on Windows.** Coverage includes
success, preflight failure, failure before output, partial output, missing/stale/
malformed responses, disagreement between counts and files, late failure, code
mismatch/drift, and refusal to seal an unconfirmed process tree. Real child-process
tests verify that descendant file writes stop after timeout or parent exit.

A real probe of the Python 3.10.21 Conda worker confirmed matching code hashes at
both checkpoints and a clean process-tree exit. It inspected the environment and
loaded no checkpoint or biometric input. New v3 biometric inference was not needed
for this correction; the numerical adapters and original results are unchanged.

The original P1 run was revalidated read-only with the corrected verifier:

| Check | Result |
|---|---|
| Source-image SHA-256 | 100/100 verified |
| Frozen pairs and side/order bindings | 250/250 consistent |
| Point, descriptor and source-index arrays | 100/100 exact |
| Raw scores and statuses | 250/250 exact; three valid zeros |
| Coordinator error / worker acknowledgement | No error; matching successful acknowledgement |
| Recorded extraction and matcher counts | 100 fresh extractions, 250 matches, zero failures |
| Original run files | 434 unchanged |
| Overall result | `approved=true`, `passed_legacy_evidence` |

The v2 run did not record worker source attestation at both execution boundaries,
coordinator end-of-run drift checks or explicit process-tree termination evidence.
These cannot be established retroactively. The legacy result confirms consistency
of the evidence that actually exists: sealed files, original code snapshot and
request bindings, acknowledgements, environments and observed counts. New v3
runs require the additional records. This distinction is explicit in the
[filtered closure evidence](evidence/step01-closure.json).

Local detailed evidence is under `workspace/review-step01-closure/`, including the
supplied review/probe, source checks, test logs, fresh worker probe and the new
`revalidation-final/` report. Original migration reports and Dahia response bytes
remain untouched. Public evidence contains aggregate counts and source hashes,
without subject identifiers, machine paths or individual research scores.

## Local agent context and boundary

`AGENTS.md` exists at the project root, is maintained locally and was explicitly
read during this correction. It and the local agent-loading note are excluded
through `.git/info/exclude`. Their absence from the public tree is intentional;
public documentation is the filtered review entry point.

Step 01 is closed by this correction and the existing-evidence revalidation.
Dahia's two weights remain access-blocked. The review's proposed
`Survey f40 → Direct Pore → spatial` composition is a possible later task and has
not been implemented or evaluated here. No new inference, training, P2, SD300C,
protected-cohort access or population expansion was performed.
