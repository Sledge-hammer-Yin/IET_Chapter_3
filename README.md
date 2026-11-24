# UAV positioning experiments for Chapter 3

This project contains reproducible positioning experiments for Sections 3.4 and 3.5.
B1 to B3 compare GNSS/IMU estimators on two UrbanNav ground-vehicle sequences.
LC, TC-Pose and TC-Surface compare three GLIO-based configurations on Deep-Urban-1.
Each group has its own shared inputs, initialization and evaluation protocol.
Do not combine the two groups into one six-method accuracy ranking.
The UrbanNav studies use a ground vehicle. UTIL provides recorded UAV flights, but
this repository does not establish onboard real-time performance. The Section 3.4
methods require no trained weights.

## Algorithm map and trade-offs

| Experiment | Method | Main idea | Chapter section | Main advantage | Main limitation |
|---|---|---|---|---|---|
| Conventional GNSS/IMU | B1 | GNSS/IMU error-state Kalman filter (ESKF) | 3.4.1 and 3.4.2 | Simple causal baseline | Sensitive to model errors and bad fixes |
| Conventional GNSS/IMU | B2 | B1 with normalized innovation squared (NIS) rejection | 3.4.3 | Rejects isolated inconsistent fixes | May reject useful fixes after drift |
| Conventional GNSS/IMU | B3 | Fixed-lag factor graph with IMU preintegration | 3.4.1, 3.4.4 and 3.4.5 | Uses temporal constraints in a window | More computation; no robust GNSS loss here |
| GLIO | LC | GNSS position factors with LiDAR/IMU odometry | 3.4.6 | Simple position-level interface | Depends on the quality and availability of position fixes |
| GLIO | TC-Pose | Double-difference pseudorange with relative-pose constraints | 3.4.6 | Uses raw GNSS structure more directly | More nonlinear and initialization-sensitive |
| GLIO | TC-Surface | Double-difference pseudorange with LiDAR surface constraints | 3.4.6 | Adds scene geometry to the tight coupling | Highest resource cost; depends on scene geometry |
| Learning-aided GNSS | WLS | Weighted least squares with fixed measurement weights | 3.5.2 | Training-free and transparent | Fixed weights do not adapt well to multipath |
| Learning-aided GNSS | TDL-W | Learned satellite weights | 3.5.2 | Adapts measurement reliability | No explicit bias correction; needs representative training |
| Learning-aided GNSS | TDL-B | Learned pseudorange bias correction | 3.5.2 | Corrects repeatable measurement bias | Does not learn measurement weights |
| Learning-aided GNSS | TDL-BW | Joint learned bias and weight prediction | 3.5.2 | Combines the two correction mechanisms | More model dependence and training cost |
| UWB/inertial fusion | ESKF | Fixed-noise UWB/IMU filter | 3.5.6 | Simple training-free baseline | Sensitive to biased time-difference-of-arrival measurements |
| UWB/inertial fusion | Huber-ESKF | Robust Huber measurement update | 3.5.5 and 3.5.6 | Reduces the influence of large residuals | A fixed threshold cannot learn systematic bias |
| UWB/inertial fusion | NN-ESKF | Learned UWB bias correction before filtering | 3.5.3, 3.5.5 and 3.5.6 | Corrects repeatable data-driven bias | Needs training; no direct NLOS label is evaluated |
| UWB/inertial fusion | NN-Huber-ESKF | Learned correction with a robust update | 3.5.3, 3.5.5 and 3.5.6 | Combines bias correction and residual robustness | Most complex and dataset-dependent |
| Inertial odometry | IMU integration | Direct inertial propagation | 3.5.4 | Training-free reference baseline | Accumulated drift grows rapidly |
| Inertial odometry | Fixed position | Stationary prediction control | 3.5.4 | Exposes metric and data-split limitations | Not a navigation estimator; ignores motion |
| Inertial odometry | TLIO-adapted | Learned motion with a stochastic-cloning ESKF | 3.5.4 | Greatly reduces free-integration drift | Higher absolute error than the fixed control on this split |
| Inertial odometry | AirIO-Net + ESKF | Learned velocity aiding in an ESKF | 3.5.4 | Best tested relative-displacement result | Needs training; onboard timing and covariance calibration are unverified |

Section 3.5.1 defines the learning-aided taxonomy used by the Section 3.5 rows;
the implemented comparisons are reported in Sections 3.5.2-3.5.6.

Book section numbers are used here. Some Word drafts display 1.4 instead of 3.4.
See [the section index](chapters/README.md) for current and planned sections.
Section 3.5 contains learning-aided experiments. No Section 3.6 experiment is included.

## Public datasets and fixed splits

| Experiment | Public dataset | Use in this repository |
|---|---|---|
| B1 to B3 | [UrbanNav](https://github.com/IPNL-POLYU/UrbanNavDataset) | Deep-Urban-1 and Medium-Urban-1 evaluation with GNSS, IMU and reference trajectories |
| GLIO | [UrbanNav](https://github.com/IPNL-POLYU/UrbanNavDataset) | Deep-Urban-1 evaluation with GNSS, IMU, LiDAR and the same reference source |
| Learning-aided GNSS | [KLT](https://github.com/ebhrz/KLTDataset) and [UrbanNav](https://github.com/IPNL-POLYU/UrbanNavDataset) | KLT1_203 and KLT2_209 train, KLT3_404 validates, and Deep-Urban-1 tests the models |
| UWB/inertial fusion | [UTIL](https://utiasdsl.github.io/util-uwb-dataset/) | Constellations 1-2 train, constellation 3 validates, and nine constellation-4 flights test the models using IMU and TDoA2 measurements |
| Inertial odometry | [EuRoC MAV](https://projects.asl.ethz.ch/datasets/euroc-mav/) | Five sequences train, one validates, and five test the models using IMU and reference states only |

Raw datasets are not stored in this repository. Exact files, sequence lists and
download steps are in the [Section 3.4 data guide](datasets/README.md) and the
[Section 3.5 data guides](datasets/LearningAid/README.md).

## Run B1 to B3

The prepared environment is `C:\UAV_Chapter3\.envs\b123`. It leaves the existing Conda environments unchanged. From PowerShell:

```powershell
Set-Location C:\UAV_Chapter3\IET_Chapter_3
.\run_benchmark.ps1
```

If PowerShell blocks local scripts, run Python directly without changing the execution policy:

```powershell
& C:\UAV_Chapter3\.envs\b123\python.exe C:\UAV_Chapter3\IET_Chapter_3\run.py all
```

Run one method, regenerate figures, or run the physics checks:

```powershell
.\run_benchmark.ps1 -Action run -Sequence Deep-Urban-1 -Method B1_ESKF
.\run_benchmark.ps1 -Action plot
.\run_benchmark.ps1 -Action test
```

After a single-method rerun, use `-Action summarize` and `-Action plot` to update the tables and figures. A short check is available through `python run.py run --sequence Deep-Urban-1 --method B1_ESKF --max-seconds 60`; short outputs are kept separately under `results/smoke` and never enter the final metrics.

To recreate the Windows environment, use Conda from Anaconda Prompt:

```text
conda create --prefix C:\UAV_Chapter3\.envs\b123 --file C:\UAV_Chapter3\IET_Chapter_3\environment-win-64.lock.txt
```

Alternatively, use `conda env create --prefix C:\UAV_Chapter3\.envs\b123 --file environment.yml`. The lock file pins the tested Windows binaries; the YAML lists the main dependencies. On a fresh checkout, run `python run.py install-rtklib` in that environment to obtain the pinned external frontend files. Internet access is needed only to install dependencies or download the data and RTKLIB, not to run the prepared benchmark. Both setup steps have already been completed on this machine.


## GLIO code and runs

The original upstream revision is `332d19ff641f2ada9d9d75f2a6dab013d6015f76`. The exact estimator changes are
in [source.patch](algorithms/GLIO/source.patch). The local working project may
contain a Git submodule at `algorithms/GLIO/upstream`. The manual upload export
excludes that third-party checkout, its Git metadata and its original comments.
The export uses [a pinned source manifest](algorithms/GLIO/source_lock.json) and
[a source fetcher](algorithms/GLIO/fetch_upstream.py) instead.

```powershell
python algorithms/GLIO/fetch_upstream.py
```

The fetcher clones into the sibling `external/GLIO` folder, checks the base commit,
checks the patch and applies it. It does not compile, download sensor data, run
experiments or upload anything. Existing nonmatching work is not overwritten.
Preserve upstream licenses and notices.

GLIO runs on the existing Ubuntu/ROS server. Read
[the GLIO guide](algorithms/GLIO/README.md) and
[the common-epoch report](results/GLIO/Deep-Urban-1/Comparison_calibrated_v2/COMPARISON_REPORT.md).
Full Linux workspace and setup archives are private local backups; they are not
part of this upload tree and cannot be executed as Windows binaries.

## Learning-aided positioning

Section 3.5 adds separate GNSS, UWB/inertial and inertial-odometry comparisons.
Read [the Section 3.5 guide](chapters/section_3_5/README.md) for data, setup,
validation and run commands. [Saved results](results/LearningAid/20261107_cpu_v1/README.md)
include English tables and three Times New Roman figures. The inertial comparison
includes its fixed-position control and negative absolute-error result.
Validate saved outputs with `python scripts/LearningAid/run.py validate`.
Raw datasets and installed environments are not uploaded. Recorded model weights are available in the [Section 3.5 release](https://github.com/Sledge-hammer-Yin/IET_Chapter_3/releases/tag/chapter3-learning-20261107).
Run `python algorithms/LearningAid/fetch_models.py` to download and check them.

## Saved result previews

All previews below are static, single-panel English figures. The plotted methods
within each figure share one evaluation protocol. Cross-figure rankings are invalid.

### Sections 3.4.1-3.4.5: conventional GNSS/IMU estimation

<img src="results/figures/Deep-Urban-1_error.png" width="760" alt="B1 to B3 3D position error on UrbanNav Deep-Urban-1">

*Three-dimensional position error on Deep-Urban-1. The logarithmic axis shows both
ordinary errors and long urban degradation. See the [metric table](CHAPTER3_RESULTS.md)
for both UrbanNav sequences.*

### Section 3.4.6: GLIO fusion configurations

<img src="results/GLIO/Deep-Urban-1/Comparison_calibrated_v2/comparison_position_error.png" width="760" alt="GLIO configuration position errors on UrbanNav Deep-Urban-1">

*Common-epoch three-dimensional position error for LC, TC-Pose and TC-Surface.
See the [GLIO report](results/GLIO/Deep-Urban-1/Comparison_calibrated_v2/COMPARISON_REPORT.md).*

### Section 3.5.2: learning-aided GNSS

<img src="results/LearningAid/20261107_cpu_v1/figures/urbannav_gnss_error_cdf.png" width="760" alt="Learning-aided GNSS position error distributions on UrbanNav">

*Empirical cumulative distributions of three-dimensional GNSS position error.
The learned weighting and joint correction shift the tested distribution toward
smaller errors than WLS.*

### Sections 3.5.3, 3.5.5 and 3.5.6: UWB/inertial fusion

<img src="results/LearningAid/20261107_cpu_v1/figures/util_uwb_error_cdf.png" width="760" alt="UWB and inertial fusion position error distributions on UTIL">

*Empirical cumulative distributions on the held-out UTIL flights. The combined
learned correction and robust update gives the smallest tested error distribution;
this experiment does not report an NLOS-classification score.*

### Section 3.5.4: deep inertial odometry

<img src="results/LearningAid/20261107_cpu_v1/figures/euroc_relative_error.png" width="760" alt="Relative inertial odometry errors on the EuRoC test sequences">

*Ten-second relative-displacement RMSE on the EuRoC test sequences. The fixed-position
control is retained: it has lower absolute RMSE than the learned methods, while
AirIO-Net + ESKF gives the best tested relative-displacement result. Full tables are
in the [Section 3.5 result report](results/LearningAid/20261107_cpu_v1/README.md).*

## Files

| Folder | Purpose |
|---|---|
| `algorithms` | B1 to B3, shared geometry and GLIO source access |
| `configs` | B1 to B3 settings and the three GLIO profiles |
| `evaluation` | Metrics, plotting and evaluator checks |
| `scripts/GLIO` | Copies of the existing server workflow scripts |
| `results` | Saved small trajectories, figures, metrics and reports |
| `datasets` | Adapters, public links and download instructions; no full datasets |
| `chapters` | Section-to-method index and future section placeholders |

B1 to B3 data stay in `C:/UAV_Chapter3/data`. GLIO sensor data remain on the server.
The [B1 to B3 report](CHAPTER3_RESULTS.md) and [GLIO report](results/GLIO/Deep-Urban-1/Comparison_calibrated_v2/COMPARISON_REPORT.md)
describe the measured results and manuscript placement.
Follow [manual upload instructions](GITHUB_SYNC.md). No upload is performed by the tools here.
