# Python and Conda policy

Decision made and checked on **2026-09-13**. The development environment is
**CPython 3.13.15, standard GIL build, managed by the existing Miniconda**.
This is the current project standard, not an unresolved future choice.

## Why 3.13

Python 3.13 combines a current interpreter with broad scientific and ML binary
availability. The [Python support table](https://devguide.python.org/versions/)
lists its support through October 2029. Python 3.12 has a shorter remaining
support window, and 3.10 is retained only for the historical P1 worker.

The public PyPI file inventories were checked for Windows x86-64 wheels for
NumPy, SciPy, pandas, PyArrow, scikit-image, scikit-learn, OpenCV, PyTorch,
TensorFlow and ONNX Runtime. All ten had compatible CPython 3.13 distributions.
TensorFlow 2.21.0 had a 3.13 Windows wheel and no 3.14 Windows wheel in the
[checked release inventory](https://pypi.org/pypi/tensorflow/2.21.0/json).
That is the concrete compatibility reason for selecting 3.13 over 3.14 now.
This checks artifact availability, not installation/inference of ten frameworks.
The dated full inventory is local in
`workspace/review-conda-migration/python-compatibility.json`.

The free-threaded Python build is deliberately not selected. The environment
declaration selects the ordinary `cp313` build to keep native extension ABI
requirements consistent with the checked wheels. Python 3.13.15 is available in
the selected Conda channel and was installed and executed locally.

## Two installed profiles

| Profile | Interpreter | Responsibility |
|---|---|---|
| `.conda/dev` | Python 3.13.15 | Development, protocol, import, orchestration, NumPy 2.5.2 reporting, tests and Ruff |
| `.conda/p1` | Python 3.10.21 | CPU P1 model execution with the historical NumPy/Torch/OpenCV versions |

The new P1 environment was recreated through Conda and pip package definitions.
It is not the previous venv moved to a new directory. The central process does
not import Torch/OpenCV. A versioned JSON request supplies opaque image records
and pairs to a separately activated process; pair truth and cohort selection
stay in the coordinator. Model execution and its numerical libraries stay in
the worker.

The worker imports only its own implementation and a small shared module closure.
Ruff targets Python 3.13 for development code and Python 3.10 for that closure.
The shared package's `requires-python >=3.10` permits installing the worker;
it does not designate Python 3.10 as the development interpreter.

Native Conda packages are resolved from **conda-forge only**, with strict channel
priority and no defaults mixing. The existing Miniconda installation manages
environments; nothing is installed into its base. Environment creation and CLI
helpers use project-local prefixes and `conda run`; no global shell initialization
is required. See [Conda's environment documentation](https://docs.conda.io/projects/conda/en/stable/user-guide/tasks/manage-environments.html).

## Reproducibility and upgrades

`environments/dev.yml` and `p1.yml` explain the intended native dependencies.
`environments/locks/*-win-64.explicit.txt` pin exact native package builds and
checksums for the tested platform. `environments/locks/p1-pip.txt` pins only
pip-owned worker dependencies. Python and bootstrap tools remain Conda-owned.
Install native dependencies before pip dependencies and install this repository
separately with `--no-deps -e .`. `pip check` is required in both profiles.

Recreate an environment when changing its dependency plan; do not repeatedly
mix ad hoc Conda and pip solver updates. An initial legacy freeze overlaid
packaging tools during migration. P1 was ultimately recreated from the final
locks, and the bootstrap checks installed metadata uniqueness and pip's actual
version as well as dependency consistency. Full local inventories and exact
native locks record the final state. The final P1 run follows that clean rebuild.

Upgrade the development interpreter deliberately: check Windows wheels, solve a
fresh profile, run default tests and worker-boundary checks, then validate any
affected real route before replacing the previous environment. Update the YAML,
locks, bootstrap version assertions, local interpreter selection and documentation
together. A new model with
conflicting Python, CUDA or native dependencies receives its own Conda worker
profile; it must not force a downgrade of the central development interpreter.

Conda does not erase framework/GPU/OS constraints. GPU workers need their own
verified runtime matrix. The [TensorFlow installation documentation](https://www.tensorflow.org/install/pip)
separately describes native-Windows and WSL GPU support. No CUDA, driver, WSL,
TensorFlow installation or new model route was added in this environment task.

Historic runs, reference manifests and Dahia access evidence remain relevant
scientific provenance and are preserved. Obsolete environments, duplicate
imports and invalidated disposable caches are removed only after replacement
validation, with a local cleanup inventory.
