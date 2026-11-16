# Learning-aided positioning methods

This folder contains the shared experiment code for Section 3.5, displayed as 1.5
in some Word drafts. The [chapter guide](../../chapters/section_3_5/README.md)
contains setup and run commands. The [configuration](../../configs/LearningAid/README.md)
records the frozen settings. No full raw dataset or installed environment is included.

| File | Purpose |
|---|---|
| `common.py` | Shared paths, metrics, seeds and figure style |
| `prepare_gnss.py`, `run_gnss.py` | GNSS features and learning-head comparison |
| `run_uwb.py` | Shared UWB/inertial filter with correction and robust-update variants |
| `prepare_io.py`, `run_io.py` | IMU-only adapter and learned inertial constraints |
| `benchmark_and_diagnostics.py` | GNSS timing and fixed-position diagnostic |
| `generate_results.py`, `validate_results.py` | Tables, figures and saved-result checks |
| `fetch_upstream.py`, `source_lock.json` | Fixed source revisions and runtime file hashes |
| `fetch_models.py`, `models.json` | Recorded trained weights and checksums |

Upstream implementations are fetched outside the repository. Keep their licenses
and notices. The experiment harness does not replace or relicense upstream code.
The three single-output GNSS ablations use the original shared architecture.
The UWB model is a controlled adaptation inspired by the cited bias method.
The inertial experiment adapts the published networks and retains its stated limits.
