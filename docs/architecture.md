# Architecture and extension boundaries

## Development coordinator and P1 worker

```text
Miniconda .conda/dev — Python 3.13
  CLI → protocol validation → runner → JSON request
                                      │ conda run, separate process
Miniconda .conda/p1 — Python 3.10       ▼
  worker → Survey f40 → SIFT → spatial → JSON response + immutable arrays
                                      │
Development coordinator ← run sealing ┘
  verification → comparison report
```

`protocol.py` validates imported development metadata and frozen pair order.
The importer is the only module reading the previous project's artifacts; it
never imports or executes that package. `inputs.json` and `pairs.json` expose
opaque keys. Truth and subject identifiers stay in the reference protocol.

`runner.py` validates configuration, snapshots source and dispatches a P1 job.
`process.py` activates the configured Conda prefix and invokes `fpl3.worker` with
a versioned file/JSON request, without a shell. The request is fingerprinted, the
worker verifies its interpreter prefix, and the coordinator rejects a missing,
stale or mismatched response. Logs are separate from JSON data. The worker's
image/pair field allowlist rejects truth and duplicate bindings.

`worker.py` verifies the historical numerical runtime and component closure,
checks each source image, extracts once per image and matches opaque pairs.
Only that environment imports Torch and OpenCV during execution. `results.py`
shares pair execution and coverage; `worker_protocol.py` shares the wire version.
The worker does not import the coordinator, importer or protocol.

The worker and its small shared dependency closure retain Python 3.10-compatible
syntax. Other modules and tests use the Python 3.13 development target. Ruff
records both targets. Package metadata permits Python 3.10 because the same
package supplies the legacy process endpoint; supported development is 3.13.
Do not import modern-only coordinator modules from the worker. This separation
allows an environment upgrade without upgrading every model dependency.

## Scientific contracts and extension points

`contracts.py` defines image content/resolution/geometry, points, descriptor
mapping and match results. Points use zero-based **x=column, y=row**, in native
image pixels. Descriptors retain points and integer source indices. Validation
rejects wrong frames, duplicate indices, nonfinite values and inconsistent scores.

`biometrics.py` supplies thin Survey f40 and Dahia SIFT/spatial adapters. Required
author source lives in ignored `workspace/third_party`. P1 tiling and operation
order preserve the earlier experiment. An explicit factory mapping selects
components. In an authorized future task, implement the existing interface,
register the factory and select it in configuration. The synthetic subset
descriptor test proves replacement without changing pair execution or coverage.
The current P1 CLI accepts only its historical composition and parameters.

`ImagePairSystem.compare(left, right)` is an extension point for a whole external
system that does not expose separate stages. No generic engine, dynamic plugin
loader or untested model route is included. Future incompatible models should
receive their own declared Conda profile and narrow process contract when that
model work is authorized. A Conda manager cannot make incompatible libraries
compatible inside one interpreter.

`cache.py` binds features to source bytes/geometry, parameters, component and
weight hashes, numerical identity and executed source. NPZ files contain source
points, retained points, descriptors and indices. Metadata validates payload
hashes. Fresh inference bypasses reuse and preserves arrays before cache checks.

`verification.py` compares arrays, statuses and scores with the reference without
running a model or adjusting scores. Exact parity was fixed before comparison.
NPZ container hashes establish integrity; array equality establishes parity.
`numerical.py` runs explicit synthetic model checks in the P1 worker. Default
tests need no models, data or network. `dahia.py` performs explicit public artifact
audits and non-executing archive inspection.

## Failures and finalization

Success requires a finite raw score, including zero. Extraction/matching failure
has a null score and stage/reason. Setup or worker process errors are infrastructure
blocks. Logical attempts and physical matcher calls are separate; an interrupted
process can leave the physical count unknown. Shared extraction time is counted
once, separately from matching and coordinator/process overhead.

Files are written fully before atomic non-replacing publication. New run directories
must not exist. `fpl3-run-v2` records coordinator and worker identities; a final
`complete.json` binds artifacts and executed source snapshots. Old run formats and
their original evidence remain intact. This is a bounded worker integration,
without a general resume/retry or scheduling engine.
