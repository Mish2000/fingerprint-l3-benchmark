# Fingerprint research projects

Four public repositories cover different questions and engineering layers in
this research effort. **fingerprint-l3-benchmark is the current research home.**
The other repositories retain a completed comparison, an ML/CV case study and
a working software demonstration, each with its own evidence and limits.

| Repository | Role | What to inspect |
|---|---|---|
| [fingerprint-l3-benchmark](../README.md) | Current Level-3 research home | Learned pore detection, SIFT/DP32 compositions, controlled protocols, isolated model execution and source-bound results on native high-resolution inputs |
| [fingerprint-benchmark](https://github.com/Mish2000/fingerprint-benchmark) | Completed comparison at a shared 500 PPI processing resolution | Six declared verification routes, fixed comparison coverage, integration engineering and validated result bundles |
| [fingerprint-new-method](https://github.com/Mish2000/fingerprint-new-method) | ML/CV case study | A U-Net trained for localization against synthetic pore annotations, grouped data splits and an inconclusive synthetic-to-real transfer assessment |
| [fingerprint-research](https://github.com/Mish2000/fingerprint-research) | Software workbench | React/TypeScript, FastAPI, PostgreSQL/pgvector and Java SourceAFIS connected in a tested local verification and identification workflow |

## Reading paths

- **Continuing research:** start with the [current README](../README.md),
  [candidate status](status.md) and [research context](research-context.md).
  Step 03 is complete. Further experiments require a separately defined protocol;
  the current compositions do not establish anatomical pore accuracy or a new
  state-of-the-art matcher.
- **ML and computer vision:** read the
  [pore-localization case study](https://github.com/Mish2000/fingerprint-new-method/blob/main/docs/case-study.md).
  Its synthetic localization result and real-data transfer limitation belong
  together. That repository's experiments are currently paused.
- **Python and experiment infrastructure:** inspect the
  [completed benchmark](https://github.com/Mish2000/fingerprint-benchmark)
  and its
  [final report](https://github.com/Mish2000/fingerprint-benchmark/blob/main/evidence/final-baseline-tar-far-frr/final-baseline-report.md).
  Source scan resolution and the common 500 PPI processing profile are distinct.
- **Application and systems engineering:** use the
  [workbench](https://github.com/Mish2000/fingerprint-research) and its
  [engineering case study](https://github.com/Mish2000/fingerprint-research/blob/main/docs/ENGINEERING_CASE_STUDY.md).
  Its software demo is operational; full reconstruction of older experiments
  still requires missing original manifests. It is a research prototype, not a
  certified identity or security product.

## How the evidence fits together

The completed benchmark provides comparison infrastructure and recorded
500 PPI results. The current research home focuses on routes that actually use
fine-detail predictions on native high-resolution inputs. The ML/CV case study
examines a separate localization and transfer question. The workbench demonstrates
how computer vision, model inference, storage and an external Java engine can be
connected in an application.

These roles do not make their metrics interchangeable. Each result stays bound
to its original inputs, protocol, implementation and numerical environment.
Related scans are not independent populations; moving work between repositories
does not erase earlier exposure. Localization F1 is not identity-verification
accuracy, and successful software tests are not biometric-performance evidence.

Earlier exploratory implementations remain in local historical checkouts. This
page defines the public reading path without migrating their code, rerunning
experiments or changing frozen evidence. The detailed Level-3 candidate status
continues to have one source of truth in [status.md](status.md).
