# UAV positioning experiments for Chapter 3

This project contains the conventional positioning examples for Section 3.4.
B1 to B3 compare GNSS/IMU estimators on two UrbanNav ground-vehicle sequences.
LC, TC-Pose and TC-Surface compare three GLIO-based configurations on Deep-Urban-1.
Each group has its own shared inputs, initialization and evaluation protocol.
Do not combine the two groups into one six-method accuracy ranking.
These experiments do not validate UAV flight performance. No trained weights are required.

| Method | Main idea | Chapter section | Results |
|---|---|---|---|
| B1 | GNSS/IMU ESKF | 3.4.1 and 3.4.2 | `results/Deep-Urban-1` and `results/Medium-Urban-1` |
| B2 | B1 with NIS observation rejection | 3.4.3 | Same two sequence folders |
| B3 | GNSS/IMU fixed-lag factor graph with preintegration | 3.4.1, 3.4.4 and 3.4.5 | Same two sequence folders |
| LC | GNSS position factors with LiDAR/IMU odometry | 3.4.6 | `results/GLIO/Deep-Urban-1/Comparison_calibrated_v2` |
| TC-Pose | DD pseudorange with relative pose constraints | 3.4.6 | Same GLIO result folder |
| TC-Surface | DD pseudorange with LiDAR surface constraints | 3.4.6 | Same GLIO result folder |

Book section numbers are used here. Some Word drafts display 1.4 instead of 3.4.
See [the section index](chapters/README.md) for current and planned sections.
Folders for 3.5 and 3.6 are reserved; no implementations or results are claimed there.

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
