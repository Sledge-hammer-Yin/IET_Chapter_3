# Data and upstream software

The actual benchmark uses **UrbanNav-HK-Deep-Urban-1** and **UrbanNav-HK-Medium-Urban-1**. Each run needs GNSS RINEX, Xsens IMU CSV, calibration and the official SPAN-CPT/IE reference file. No ROS, Ubuntu, LiDAR, image or UWB download is required for B1--B3.

Official index: [UrbanNav](https://github.com/IPNL-POLYU/UrbanNavDataset). Dataset paper: [Hong Kong UrbanNav, NAVIGATION 70(4), 2023](https://doi.org/10.33012/navi.602). Both sequences have 1 Hz reference files; their quality codes vary. The benchmark includes all available matched reference epochs without claiming an identical reference accuracy everywhere.

## Download links

| Sequence | GNSS files | Xsens CSV | Reference |
|---|---|---|---|
| Deep-Urban-1 | [Official folder](https://www.dropbox.com/sh/7ox7718bzcjqtlf/AABH_Kjm65gHQ09K3antBRdua?dl=0) | [IMU](https://www.dropbox.com/s/pet3up4vka61jop/xsense_imu_deep_urban1.csv?dl=0) | [Reference](https://www.dropbox.com/s/ej2mkue2w3r36s2/UrbanNav_whampoa_raw.txt?dl=0) |
| Medium-Urban-1 | [Official folder](https://www.dropbox.com/sh/2haoy68xekg95zl/AAAkcN4FwhFxkPY1lXsxbJrxa?dl=0) | [IMU](https://www.dropbox.com/s/2rh1rs15ihpf63u/xsense_imu_medium_urban1.csv?dl=0) | [Reference](https://www.dropbox.com/s/twsvwftucoytfpc/UrbanNav_TST_GT_raw.txt?dl=0) |

Calibration and noise: [Deep](https://github.com/IPNL-POLYU/UrbanNavDataset/tree/master/UrbanNav-HK-Deep-Urban-1), [Medium](https://github.com/IPNL-POLYU/UrbanNavDataset/tree/master/UrbanNav-HK-Medium-Urban-1). The official index is the source for any revised download URL.

## Exact local files used

All paths below are relative to `C:\UAV_Chapter3\data\raw\UrbanNav`.

```text
Deep-Urban-1/
  imu/xsense_imu_deep_urban1.csv
  gnss/20210521.medium-urban.whampoa.ublox.f9p.obs.txt
  gnss/hksc1410.21o.txt
  gnss/hksc141g.nav.txt
  ground_truth/UrbanNav_whampoa_raw.txt
  calibration/extrinsic.yaml
  calibration/xsens_imu_param.yaml
Medium-Urban-1/
  imu/xsense_imu_medium_urban1.csv
  gnss/UrbanNav-HK-Medium-Urban-1.ublox.f9p.splitter.obs
  gnss/hksc137c.21o
  gnss/hksc137c.nav
  ground_truth/UrbanNav_TST_GT_raw.txt
  calibration/extrinsic.yaml
  calibration/xsens_imu_param.yaml
```

The Deep files' extra `.txt` extensions are kept exactly as downloaded; RTKLIB reads their RINEX contents. The names `medium-urban.whampoa` and `light-urban.tste` in the original downloads do not change the official sequence labels. Medium uses the single `splitter.obs` stream for every estimator, without method-dependent receiver switching. The dataset maintainers note an F9P malfunction in [issue 11](https://github.com/IPNL-POLYU/UrbanNavDataset/issues/11); the frontend availability figures in the results should be checked, rather than assuming a continuous GNSS solution.

`prepare.py` writes shared `inputs.npz`, separate `reference.npz`, small forward GNSS solutions and a source/configuration/hash manifest under `C:\UAV_Chapter3\data\processed\<sequence>`. Raw files are read only. Sensor-only inputs and reference data are separate so the estimators never need to open reference data. Cached input settings, source size/mtime and RTKLIB binary hash are checked before reuse; use `python run.py prepare --force` after deliberately replacing a source file without changing its size and modification time.

## Software links and versions

- [GTSAM 4.2](https://github.com/borglab/gtsam/tree/4.2): B3 actually uses its Windows Conda package and `gtsam_unstable` fixed-lag smoother. See the environment lock file for the exact build.
- [RTKLIB source](https://github.com/tomojitakasu/RTKLIB/tree/rtklib_2.4.3) and [official 2.4.3 binaries](https://github.com/tomojitakasu/RTKLIB_bin/tree/rtklib_2.4.3): the shared GNSS frontend uses `rnx2rtkp` 2.4.3 b34. `rtklib_binaries.json` lists the exact official URLs, sizes and SHA-256 values of the downloaded executable, dependencies and license. Use `python run.py install-rtklib` only if these files are missing.
- [KF-GINS](https://github.com/i2Nav-WHU/KF-GINS): downloaded reference implementation; its native algorithm is not executed or reported as B1.
- [GLIO](https://github.com/XikunLiu-huskit/GLIO): context for section 1.4.6, not run here. This benchmark has no LiDAR factors or GLIO mode comparison.

Raw data, Conda environments, upstream source trees and executables are outside the GitHub project. Share only links, manifests, code and small derived results. Keep upstream license notices when redistributing their materials. UrbanNav's official index provides its dataset license and citation request; aggregate results may be published without redistributing the raw data.

