# Learning-aided positioning results

Recorded run: `20261107_cpu_v1`, November 7, 2026. The saved numerical artifacts
and three comparison figures are preserved from the completed server run.
There are 18 trained models, 117 main evaluations and five fixed-position diagnostics.

Seeds are 7, 19 and 42. The tables pool test timestamps within each seed and
report the mean and sample standard deviation across seeds. Deterministic
controls run once. There is no fitted trajectory, scale or time alignment.
The ten-second relative metric measures position-displacement error, not an
SE(3) relative-pose error. No cross-dataset algorithm ranking is made.

## GNSS

| Method | 3D RMSE (m) | Horizontal RMSE (m) | 3D P95 (m) | 10 s relative RMSE (m) |
|---|---:|---:|---:|---:|
| WLS | 48.12 | 20.06 | 94.25 | 44.53 |
| TDL-W | 22.13 +/- 0.78 | 14.67 +/- 0.25 | 50.88 +/- 1.49 | 22.25 +/- 0.75 |
| TDL-B | 32.27 +/- 0.48 | 16.71 +/- 0.14 | 66.78 +/- 1.91 | 32.65 +/- 1.21 |
| TDL-BW | 21.84 +/- 0.41 | 14.19 +/- 0.27 | 50.42 +/- 0.90 | 21.30 +/- 0.42 |

## UWB

| Method | 3D RMSE (m) | Horizontal RMSE (m) | 3D P95 (m) | 10 s relative RMSE (m) |
|---|---:|---:|---:|---:|
| ESKF | 0.357 | 0.130 | 0.802 | 0.372 |
| Huber-ESKF | 0.321 | 0.112 | 0.608 | 0.298 |
| NN-ESKF | 0.261 +/- 0.002 | 0.110 +/- 0.000 | 0.462 +/- 0.014 | 0.314 +/- 0.002 |
| NN-Huber-ESKF | 0.217 +/- 0.001 | 0.091 +/- 0.001 | 0.386 +/- 0.005 | 0.241 +/- 0.004 |

## IO

| Method | 3D RMSE (m) | Horizontal RMSE (m) | 3D P95 (m) | 10 s relative RMSE (m) |
|---|---:|---:|---:|---:|
| IMU integration | 521.33 | 518.06 | 1269.15 | 127.35 |
| TLIO-adapted | 8.30 +/- 3.51 | 7.32 +/- 3.15 | 15.95 +/- 6.12 | 5.19 +/- 0.12 |
| AirIO-Net + ESKF | 7.34 +/- 0.77 | 6.08 +/- 0.72 | 13.77 +/- 2.68 | 3.43 +/- 0.06 |
| Fixed position | 5.25 | 5.18 | 11.93 | 4.58 |

## Interpretation

GNSS learned weighting and joint correction reduce errors in the tested vehicle
sequence. Variable reference quality and platform differences limit the claim.
UWB bias correction and robust updating work well together for these flight records.
No flight NLOS classification score is claimed.
Both learned inertial configurations reduce free-integration drift. The fixed-position
control has lower absolute RMSE than either learned method. Only the velocity-aided
configuration improves the ten-second relative metric against that control.
This is a limited-training diagnostic, not a full published AirIO reproduction.
AirIMU is not used. Onboard timing and covariance calibration are not established.

## Figures and files

- `figures/urbannav_gnss_error_cdf.png` and `.pdf`: GNSS error distributions.
- `figures/util_uwb_error_cdf.png` and `.pdf`: UWB/inertial error distributions.
- `figures/euroc_relative_error.png` and `.pdf`: relative inertial errors by sequence.
- Group folders contain trajectories, metrics, training histories and seed summaries.
- `provenance.json` records the original server sources and package versions.
- `MIGRATION.json` records the local layout changes and preserved artifact hashes.
- `SHA256SUMS.txt` checks this publication package.

All figures use Times New Roman and a single set of axes. The PDFs embed the font.
Original manuscript paths, obsolete insertion advice and server cleanup logs are
kept in the private backup. They are not needed to reproduce these results.

Run `python scripts/LearningAid/run.py validate` from the repository root.
Validation needs saved outputs and NumPy, not raw datasets or model weights.
Use the `plot` action to regenerate figures in a separate new directory.
