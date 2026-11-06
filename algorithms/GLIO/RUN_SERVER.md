# GLIO on the TASLAB server

## Current completed comparison

The current controlled results are in `/data/users/taslab_zxp/outputs/GLIO/Deep-Urban-1/Comparison_calibrated_v2`. All three modes completed the
full sequence. The default runner now uses `profiles/calibrated_v2`, including
GNSS queue activation, the published antenna translation, and fixed sampling.
See `COMPARISON_REPORT.md` and `IMPLEMENTATION_AUDIT.md` in that result folder.
Earlier zero-lever-arm and short-run outputs are archived and are not mixed into
the current statistics. Legacy `configs/` records the original profile; current
configuration files are in `profiles/calibrated_v2/configs/`.

To repeat a mode with the comparison replay rate:

```bash
data_bag=/data/users/taslab_zxp/datasets/UrbanNav/Deep-Urban-1/processed/Deep-Urban-1_GLIO_input.bag
bash /data/users/taslab_zxp/projects/GLIO_setup/13_run_deep.sh LC 0 "$data_bag" 1.0
```

Substitute `TC_Pose` or `TC_Surface` for `LC`. Runs remain sequential, CPU-only,
with a private ROS master and bounded resources. The data are not copied per run.


All server artifacts belong to `/data/users/taslab_zxp`. No host package,
Docker daemon, GPU setting, or another user's file is changed.

## Environment

- Host: Ubuntu 24.04.5, AMD Ryzen 9 9950X (16 cores / 32 threads), 91 GiB RAM.
- Docker is not installed. The existing Apptainer 1.5.4 runtime works,
  including its unprivileged fakeroot mode.
- Private image: Ubuntu 18.04, ROS Melodic, bundled Ceres, GTSAM 4.0.3.
- Official GLIO commit: `332d19ff641f2ada9d9d75f2a6dab013d6015f76`.
- Compilation and runs use four logical CPUs with reduced scheduling priority.
- Solver processes have a 24 GiB virtual-memory limit.
- The private ROS master uses loopback port 11371. RViz and GPU access are off.
- The data filesystem initially had about 480 GiB free. Do not use the old
  summary's 1.8 TB figure as the current capacity.

## Server locations

| Content | Path below `/data/users/taslab_zxp` |
|---|---|
| Source and compiled nodes | `projects/GLIO_ws` |
| Scripts and independent configurations | `projects/GLIO_setup` |
| Container images, build/cache files | `installers/apptainer` |
| Dataset | `datasets/UrbanNav/Deep-Urban-1` |
| Run outputs | `outputs/GLIO/Deep-Urban-1` |
| Setup logs | `outputs/GLIO/setup` |
| Python plotting environment | `envs/glio_eval` |

## Checks in the VS Code remote terminal

```bash
bash /data/users/taslab_zxp/projects/GLIO_setup/01_check_environment.sh
```

The check is read-only. A Docker command-not-found result is expected here;
Apptainer is used instead. A generic `unshare` failure does not contradict
the successful Apptainer container test: the installed runtime has its own
administrator-provided AppArmor profile.

## Dataset

Official index: https://github.com/IPNL-POLYU/UrbanNavDataset

Deep-Urban-1 ROS data currently uses two ZIP volumes:

- `UrbanNav-HK_Whampoa-20210521_sensors.z01`: 19,327,352,832 bytes.
- `UrbanNav-HK_Whampoa-20210521_sensors.zip`: 18,439,651,312 bytes.

Both files must be together. Use the official `7z x ...sensors.zip` procedure,
not concatenation of the split volumes. Extraction checks the archive CRC.
SHA-256 files record the downloaded bytes; no author-published SHA-256 is claimed.

GNSS RINEX, reference, and calibration files are reused from the user's local
dataset. They are separate from the ROS bag. Algorithms replay only the center
LiDAR, Xsens IMU, and time-reference topics. Ground truth is not replayed.

An optional processed prefix contains actual original sensor messages and is
reindexed by ROS for early functional verification. It is explicitly incomplete
and is never labeled as the complete Deep-Urban-1 sequence.
The temporary prefix and its reindex backup were removed after full validation,
freeing about 15 GB. Their extraction scripts are retained for reproducibility.

The complete archive has now passed extraction/CRC checks. A separate compact
input, `processed/Deep-Urban-1_GLIO_input.bag`, keeps the center LiDAR, 400 Hz IMU,
and time-reference messages. Exactly one startup LiDAR scan predates the first
IMU header by about 59 ms and is omitted. All 614,782 IMU messages and 15,355
remaining LiDAR scans are retained. Message bytes and record timestamps were
verified after writing; see `processed/GLIO_input_manifest.json`. The original
archive and 68,653,442,944-byte bag are unchanged. Run commands use this compact
input by default. Use the same prepared input for all subsequent mode comparisons.
`36_prepare_input.sh` runs the preparation code inside the ROS container if the
prepared input needs to be regenerated; it refuses to overwrite an existing bag.

## Run a mode

After the full bag has been extracted:

```bash
# 120-second verification, half-speed playback.
bash /data/users/taslab_zxp/projects/GLIO_setup/13_run_deep.sh TC_Surface 120

# Complete sequence; modes are LC, TC_Pose, TC_Surface.
bash /data/users/taslab_zxp/projects/GLIO_setup/13_run_deep.sh TC_Surface 0
```

Each invocation creates its own dated output folder. Do not launch several
modes together for runtime comparisons. A lock prevents concurrent private runs.
The full-run command defaults to half-speed playback; this is not evidence of
real-time performance. The optional fourth argument selects playback rate.
The full validation in this session uses 1.0 playback after the input-coverage
check. A launch-failure watchdog stops private playback if a required node exits.

## Interpretation

The current comparison applies the published antenna translation and evaluates
all methods at the SPAN reference point using estimated attitude. Shared supplied
initial priors are retained and their derivation is unverified. The exact changes
and frozen adjacent-attitude approximation are documented in the comparison audit.
The earlier zero-lever-arm verification remains archived and is excluded from
the current statistics.

Native CSV results, a compact ENU trajectory, preliminary metrics, and two single
figures are supported. All labels are English and figures use Times New Roman.
The `smoke_*` files describe functional verification, not a final benchmark.
Book results require complete sequences, common valid evaluation epochs, reference
quality accounting, identical calibration/initialization, and declared randomness.
The full Deep-Urban-1 reference contains quality codes 1 through 5. Preliminary
evaluation reports each quality group separately without inventing accuracy bounds
for those codes. Do not compare the short GLIO checks against full-sequence B1-B3
metrics as though their evaluation intervals were identical.

GLIO's three modes compare fusion strategies within one framework. They do not
replace the independent B1/B2/B3 ESKF and factor-graph comparison. UrbanNav is a
ground-vehicle dataset and does not establish UAV flight performance.

Official algorithm: https://github.com/XikunLiu-huskit/GLIO
