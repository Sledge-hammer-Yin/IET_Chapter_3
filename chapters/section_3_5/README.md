# Section 3.5 Learning-aided UAV positioning

This section is displayed as 1.5 in some drafts. Section 3.4 remains separate.
Section 3.6 is reserved for later work.

| Experiment | Input | Methods | Chapter location |
|---|---|---|---|
| GNSS | KLT training and UrbanNav test GNSS | WLS, learned weights, learned bias, joint prediction | 3.5.1-3.5.2 |
| UWB/inertial | UTIL flight IMU and TDoA2 | fixed-noise filter, Huber update, learned bias, combined update | 3.5.3, 3.5.5-3.5.6 |
| Inertial odometry | EuRoC IMU and initial state | integration, TLIO-adapted, AirIO-Net + ESKF, fixed-position control | 3.5.4 |

## Inspect the saved results

From the repository root in a Python environment with NumPy:

```text
python scripts/LearningAid/run.py validate
```

The existing Windows B1-B3 environment can validate and redraw these saved outputs.
Do not add training dependencies to that environment. Use a separate Linux CPU
environment for full replay or training. On a fresh plotting setup install
`configs/LearningAid/requirements-plot.txt` in a separate environment.

```powershell
& C:\UAV_Chapter3\.envs\b123\python.exe scripts/LearningAid/run.py validate
& C:\UAV_Chapter3\.envs\b123\python.exe scripts/LearningAid/run.py plot
```

The plot command copies saved outputs to a new `replot_20261107_cpu_v1` folder.
It does not read raw datasets, retrain a model or overwrite the frozen results.
Choose another `--output` path if that folder already exists.
Times New Roman must be installed. On Linux set `CH3_FONT_DIR` to a directory
containing your licensed Times New Roman font files. Fonts are not distributed.

## Prepare the Linux environment

Use Python 3.12, Git and a separate CPU virtual environment. From the repository root:

```bash
python3.12 -m venv ../.envs/learning
source ../.envs/learning/bin/activate
python algorithms/LearningAid/fetch_upstream.py
python -m pip install -r configs/LearningAid/requirements-linux.lock.txt
python -m pip install --no-deps ../external/LearningAid/TASGNSS
```

The source fetcher checks five runtime repositories at the recorded commits and
verifies their Python files. The lock also records three reference-only repositories;
AirIMU is not part of the estimator. Linux binaries are not Windows binaries.

## Set paths and run

`CH3_ROOT` selects a runtime base containing `datasets` and, when needed, `tmp`.
`CH3_UPSTREAM` selects the directory containing the five upstream checkouts.
Defaults are sibling `data/LearningAid` and `external/LearningAid` folders.
`CH3_RESULTS` and `CH3_MODELS` can override result and model locations.
The checked-in configuration is `configs/LearningAid/protocol.json`.
Read the [dataset guides](../../datasets/LearningAid/README.md) before running.

```bash
export CH3_ROOT=/your/runtime/base
export CH3_FONT_DIR=/your/TimesNewRoman/fonts
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
export CUDA_VISIBLE_DEVICES=''
nice -n 19 python scripts/LearningAid/run.py gnss --output ../runs/learning-new --models ../models/learning-new
nice -n 19 python scripts/LearningAid/run.py uwb --output ../runs/learning-new --models ../models/learning-new
nice -n 19 python scripts/LearningAid/run.py io --output ../runs/learning-new --models ../models/learning-new
```

These commands run sequentially. Use a new, empty model directory to train.
Recorded weights are retained in the local backup and are not publicly hosted.
To reuse a checked local copy, pass its directory as `--models`.
`fetch_models.py` verifies the existing files against `models.json`.
Existing checkpoints are reused; this is replay, not retraining.
The `all` action also runs the timing diagnostic and creates all figures.
The `diagnostics` action reads raw inputs and completed replay outputs.
Direct legacy scripts can write to their selected output directory. Prefer the
launcher, which rejects the frozen result directory for replay and training.

## Results and limits

See the [measured result report](../../results/LearningAid/20261107_cpu_v1/README.md).
GNSS and UWB are controlled teaching examples. The inertial result must retain
its fixed-position control and negative absolute-error result. These are separate
comparisons; do not combine them with Section 3.4 into one ranking.
Model checksums are included, but trained weights are retained locally.
Raw datasets, private backups, upstream histories and installed environments
are not publication files.
