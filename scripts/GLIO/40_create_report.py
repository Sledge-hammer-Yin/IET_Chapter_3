"""Create a concise English record from completed, measured run outputs."""
import json
from pathlib import Path

root = Path('/data/users/taslab_zxp')
folder = Path((root/'outputs/GLIO/setup/full_run_output.txt').read_text().strip())
metrics = json.loads((folder/'preliminary_metrics.json').read_text())
manifest = json.loads((root/'datasets/UrbanNav/Deep-Urban-1/processed/GLIO_input_manifest.json').read_text())
drain = json.loads((folder/'backend_drain.json').read_text())
quality_table = '\n'.join('| {} | {} | {:.3f} | {:.3f} |'.format(
    row['quality_flag'], row['epochs'], row['rmse_horizontal_m'], row['rmse_3d_m'])
    for row in metrics['reference_quality_metrics'])
text = '''# Deep-Urban-1: first complete GLIO validation

The server environment is configured and GLIO TC-Surface has completed a run
using the complete prepared Deep-Urban-1 input. The three published modes also
passed separate 120-second functional checks. Full-sequence LC and TC-Pose runs
and a common-epoch comparison remain before a chapter benchmark is finalized.

## Environment and input

- Host: Ubuntu 24.04.5; AMD Ryzen 9 9950X, 16 cores / 32 threads, 91 GiB RAM.
- Runtime: existing Apptainer 1.5.4; private Ubuntu 18.04 / ROS Melodic image.
- GLIO commit: `332d19ff641f2ada9d9d75f2a6dab013d6015f76`; GTSAM 4.0.3.
- Four logical CPUs, reduced scheduling priority, 24 GiB virtual-memory limit
  per solver process; CPU-only operation and private loopback ROS master.
- Input: original 400 Hz IMU, center LiDAR, separate rover/base GNSS RINEX
  and broadcast ephemeris. No camera, UWB, or reference measurements are used
  for online updates.
- Exactly {dropped} LiDAR startup scan is excluded because its header precedes
  the first available IMU. The retained message bytes and record timestamps were
  verified after preparing the compact bag. Original archives and bag are kept.
- Input counts: {imu} IMU messages, {lidar} LiDAR scans.

## Preliminary measured results

| Method | Scored reference epochs | Horizontal RMSE (m) | 3D RMSE (m) | 3D P95 (m) |
|---|---:|---:|---:|---:|
| GLIO TC-Surface | {epochs} | {horizontal:.3f} | {rmse:.3f} | {p95:.3f} |

Maximum 3D reference-relative error: {maximum:.3f} m. No fitted trajectory
alignment is used. A 20-second settling interval is excluded, and interpolation
is accepted only across estimated-pose brackets no longer than one second.
Raw native output covers UTC {native_start:.6f} to {native_end:.6f}; scored
reference epochs cover {score_start:.0f} to {score_end:.0f}. The backend tail is
within {tail_gap:.3f} s of the final sliding-window output after the completion
wait. Replay rate is 1.0; this alone is not a real-time performance benchmark.

| Raw reference quality code | Scored epochs | Horizontal RMSE (m) | 3D RMSE (m) |
|---|---:|---:|---:|
{quality_table}

Quality codes are preserved as provided. This report does not assign an
unverified accuracy bound to each code or assume equal quality at every epoch.

## Interpretation and files

The author-provided anchor and initial Euler angles are retained; their original
derivation has not been verified. The original zero GNSS lever arm and the
uncompensated SPAN-to-IMU reference offset require an explicit calibration audit
before final accuracy claims. These are preliminary errors against the provided
reference, not a final three-method ranking or UAV flight validation.

- `preliminary_metrics.csv`: overall preliminary statistics.
- `preliminary_quality_metrics.csv`: statistics by raw reference quality code.
- `trajectory_enu.csv`: compact trajectory for further evaluation.
- `preliminary_trajectory.png` / `.pdf`: one trajectory figure.
- `preliminary_error.png` / `.pdf`: one 3D-error figure.
- `manifest.json`, `backend_drain.json`: provenance and completion checks.

Figures have English labels, Times New Roman fonts, and no subfigures. PNG files
use 300 dpi; PDF versions are vector figures.

![Horizontal trajectory](preliminary_trajectory.png)

![3D reference-relative error](preliminary_error.png)

## Repeat a run in the VS Code remote terminal

```bash
bash /data/users/taslab_zxp/projects/GLIO_setup/01_check_environment.sh
bash /data/users/taslab_zxp/projects/GLIO_setup/status.sh
# Choose LC, TC_Pose, or TC_Surface; 0 selects the complete prepared sequence.
bash /data/users/taslab_zxp/projects/GLIO_setup/13_run_deep.sh TC_Surface 0
```

The last command defaults to half-speed playback. Each run uses a separate
dated folder and a lock prevents overlapping private experiments. For a final
comparison, use identical prepared input, replay rate, initialization, and
calibration; evaluate a common valid reference-epoch set and report failures
and reference-quality groups. Keep runtime tests separate from simultaneous runs.

Official code: https://github.com/XikunLiu-huskit/GLIO

Official dataset: https://github.com/IPNL-POLYU/UrbanNavDataset
'''.format(dropped=len(manifest['dropped_startup_lidar_scans']),
           imu=manifest['retained_message_counts']['/imu/data'],
           lidar=manifest['retained_message_counts']['/velodyne_points'],
           epochs=metrics['reference_epochs'], horizontal=metrics['rmse_horizontal_m'],
           rmse=metrics['rmse_3d_m'], p95=metrics['p95_3d_m'], maximum=metrics['max_3d_m'],
           native_start=metrics['native_utc_start'], native_end=metrics['native_utc_end'],
           score_start=metrics['utc_start'], score_end=metrics['utc_end'],
           tail_gap=abs(drain['tail_gap_seconds']), quality_table=quality_table)
(folder/'RUN_SUMMARY.md').write_text(text)
(root/'projects/GLIO_setup/LATEST_RESULTS.txt').write_text(str(folder)+'\n')
print(folder/'RUN_SUMMARY.md')
