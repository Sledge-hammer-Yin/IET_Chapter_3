# Actual benchmark outputs

| Sequence | Method | 3D RMSE (m) | P95 (m) | Mean ms/epoch | Sampled RSS (MiB) |
|---|---|---:|---:|---:|---:|
| Deep-Urban-1 | B1 | 101.85 | 248.53 | 4.42 | 67.2 |
| Deep-Urban-1 | B2 | 91.11 | 204.18 | 4.49 | 81.9 |
| Deep-Urban-1 | B3 | 98.53 | 215.60 | 1.53 | 90.4 |
| Medium-Urban-1 | B1 | 35.60 | 73.87 | 4.74 | 64.6 |
| Medium-Urban-1 | B2 | 62.48 | 113.76 | 4.62 | 79.6 |
| Medium-Urban-1 | B3 | 34.52 | 58.52 | 1.58 | 87.6 |

One epoch is a 1 s input interval containing 100 IMU samples. Timing excludes input conversion and plotting. B1/B2 have Python propagation loops, while B3 calls compiled GTSAM; these timings do not establish an intrinsic algorithm-speed ranking. RSS includes the Python process and its libraries, sampled at 1 Hz.

Each sequence contains one compressed NPZ and one small metadata JSON per estimator. NPZ fields are UTC time, estimated reference-point position, velocity, biases, NIS where applicable, observation-availability/acceptance flags, epoch time, and B3 update/cost diagnostics. B3 cost values are local-window diagnostics, not an accuracy metric or a quantity directly comparable to another window.

`metrics.csv` and `metrics.json` use a common matched interval for all methods, with no trajectory alignment or method-specific trimming. `run_summary.json` records startup times, fix availability and hardware. Dataset source hashes are in `../datasets/manifests`. `source_manifest.json` records implementation/configuration hashes. `test_report.json` records the numerical checks.

The `figures` folder contains four independent figures, each as a 300 dpi PNG and a vector PDF. The two error plots use logarithmic vertical axes. No smoothing, clipped error peaks or selected best segments are used. Figures cover only the common scoring interval; startup exclusions are recorded explicitly. Recommended chapter use is described in `../CHAPTER3_RESULTS.md`.
