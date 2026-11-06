# Validation and limits

The seven numerical checks cover stationary gravity compensation and covariance positivity; analytic constant-turn motion; B1/B2 equivalence with gating disabled and outlier rejection; causal initialization; the antenna-factor Jacobian against central differences; fixed-lag marginalization; and motion through a synthetic GNSS outage and reacquisition. Test status is saved in `results/test_report.json`. Passing these checks supports implementation correctness; it does not prove accuracy or consistency for every motion/noise condition.

All six complete estimator runs finished and produced finite current-state outputs. No reference data were used by the estimators. Both sequences use identical settings, with the separate reference files opened only during evaluation. Source manifests record the exact input bytes. The explicit RTKLIB mask was checked against the earlier frontend output and produced identical GNSS positions; no GPS-only claim is made. The final B3 uses the upstream incremental fixed-lag QR solver, not a custom replacement for marginalization.

| Sequence | Input epochs | DGNSS | SPP fallback | No GNSS fix | Longest no-fix interval (s) | Startup (s) |
|---|---:|---:|---:|---:|---:|---:|
| Deep-Urban-1 | 1537 | 541 | 412 | 584 | 74 | 63 |
| Medium-Urban-1 | 786 | 207 | 209 | 370 | 59 | 101 |

| Sequence | Scoring starts (UTC) | Ends (UTC) | Reference quality-code counts |
|---|---|---|---|
| Deep-Urban-1 | 2021-05-21 06:30:18 | 2021-05-21 06:54:21 | {'1': 525, '2': 796, '3': 103, '4': 87, '5': 28} |
| Medium-Urban-1 | 2021-05-17 02:35:07 | 2021-05-17 02:46:01 | {'1': 56, '2': 590, '3': 125, '4': 16} |

The machine reports 10 physical / 16 logical CPU cores and 31.8 GiB RAM. The isolated environment uses Python 3.10.22; exact packages are pinned in `environment-win-64.lock.txt`. GPU acceleration, ROS and Ubuntu are not needed. Existing user environments and raw files are unchanged.

Important limits: this is local flat-ENU navigation with fixed gravity, without Earth/transport-rate compensation, scale-factor estimation, Doppler constraints or dedicated outage recovery. Initial yaw uses a vehicle-forward assumption. Fixed measurement-noise floors and the calibration noise interpretation are declared modeling choices, not optimized reference-error fits. Long intervals without a frontend fix and unreliable urban observations remain difficult; the plots retain the resulting large peaks. Two sequences cannot establish statistical generality, and varying SPAN reference quality prevents a blanket centimetre-accuracy claim. The comparison is internal to these implementations, not a reproduction of the published KF-GINS/GLIO results or a UAV flight validation.

Plot text, including logarithmic-axis tick labels, is configured as Times New Roman. Figures use single axes, colorblind-friendly colors, 10 pt text (9 pt ticks/legends), 1.1 pt curves and tight margins. PNG/PDF files are generated from the same figure objects. Raw IMU, intermediate covariance matrices and point clouds are not duplicated in the results. Re-running overwrites each estimator's small outputs instead of creating timestamped copies.
