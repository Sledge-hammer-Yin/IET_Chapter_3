"""Verify one GLIO run. Short-run metrics are not chapter benchmark results."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import font_manager
import matplotlib.pyplot as plt

ROOT = Path('/data/users/taslab_zxp')


def ecef(lat, lon, height):
    lat, lon = np.deg2rad(lat), np.deg2rad(lon)
    a, e2 = 6378137.0, 6.6943799901413165e-3
    normal = a / np.sqrt(1.0 - e2 * np.sin(lat)**2)
    return np.column_stack(((normal + height) * np.cos(lat) * np.cos(lon),
                            (normal + height) * np.cos(lat) * np.sin(lon),
                            (normal * (1.0 - e2) + height) * np.sin(lat)))


def enu_rotation(origin):
    x, y, z = origin
    lon = np.arctan2(y, x)
    p = np.hypot(x, y)
    lat = np.arctan2(z, p * (1.0 - 6.6943799901413165e-3))
    for _ in range(12):
        normal = 6378137.0 / np.sqrt(1.0 - 6.6943799901413165e-3 * np.sin(lat)**2)
        lat = np.arctan2(z + 6.6943799901413165e-3 * normal * np.sin(lat), p)
    return np.array([[-np.sin(lon), np.cos(lon), 0.0],
                     [-np.sin(lat)*np.cos(lon), -np.sin(lat)*np.sin(lon), np.cos(lat)],
                     [np.cos(lat)*np.cos(lon), np.cos(lat)*np.sin(lon), np.sin(lat)]])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run_dir', type=Path)
    args = parser.parse_args()
    folder = args.run_dir.resolve()
    if not str(folder).startswith(str(ROOT / 'outputs/GLIO/') + '/'):
        raise ValueError('Results must be inside the private GLIO output directory')
    mode = folder.name.split('_202')[0]
    native = folder / ('lc_result.csv' if mode == 'LC' else 'tc_batch_result.csv')
    result = np.loadtxt(native, delimiter=',', ndmin=2)
    if result.shape[1] != 12 or not np.isfinite(result).all():
        raise ValueError('Invalid native GLIO result')
    order = np.argsort(result[:, 0], kind='stable')
    result = result[order]
    # Each native batch file is rewritten with the latest estimate. Keep the
    # last occurrence if the upstream implementation emits duplicate times.
    _, last = np.unique(result[::-1, 0], return_index=True)
    result = result[np.sort(len(result) - 1 - last)]
    ref = np.loadtxt(ROOT / 'datasets/UrbanNav/Deep-Urban-1/ground_truth/UrbanNav_whampoa_raw.txt', skiprows=2)
    latitude = ref[:, 3] + ref[:, 4] / 60.0 + ref[:, 5] / 3600.0
    longitude = ref[:, 6] + ref[:, 7] / 60.0 + ref[:, 8] / 3600.0
    origin = np.array([-2419233.42, 5385473.13, 2405341.30])
    ref_enu = (ecef(latitude, longitude, ref[:, 9]) - origin) @ enu_rotation(origin).T
    # Native column 0 is the ROS message timestamp in Unix UTC seconds.
    # Do not infer or fit a time shift from errors against the reference.
    t = result[:, 0]
    if not (1621578000 < t[0] < 1621581000):
        raise ValueError('Unexpected result time convention; audit before evaluation')
    position = result[:, 9:12]
    index = np.searchsorted(t, ref[:, 0])
    valid = (index > 0) & (index < len(t))
    right = np.clip(index, 1, len(t)-1)
    valid &= (t[right] - t[right-1]) <= 1.0
    valid &= ref[:, 0] >= t[0] + 20.0
    if valid.sum() < 5:
        raise ValueError('Too few reference epochs to verify the run')
    rt = ref[valid, 0]
    estimate = np.column_stack([np.interp(rt, t, position[:, j]) for j in range(3)])
    error = estimate - ref_enu[valid]
    error3 = np.linalg.norm(error, axis=1)
    requested = int((folder / 'requested_duration_seconds.txt').read_text())
    if requested == 0:
        completion = json.loads((folder / 'backend_drain.json').read_text())
        if completion['status'] != 'complete':
            raise RuntimeError('Full-run backend completion check did not pass')
    label = 'smoke' if requested else 'preliminary'
    summary = {
        'sequence': 'Deep-Urban-1', 'mode': mode,
        'scope': 'Short-run functional verification only' if requested else 'Full-run preliminary evaluation; calibration and common-epoch audit still required',
        'native_rows': len(result), 'reference_epochs': int(valid.sum()),
        'reference_epochs_total': int(len(ref)),
        'native_utc_start': float(t[0]), 'native_utc_end': float(t[-1]),
        'utc_start': float(rt[0]), 'utc_end': float(rt[-1]),
        'rmse_horizontal_m': float(np.sqrt(np.mean(np.sum(error[:, :2]**2, axis=1)))),
        'rmse_3d_m': float(np.sqrt(np.mean(error3**2))),
        'p95_3d_m': float(np.percentile(error3, 95)),
        'max_3d_m': float(error3.max()),
        'reference_quality_counts': {str(int(q)): int(np.sum(ref[valid, 19] == q)) for q in np.unique(ref[valid, 19])},
        'alignment': 'None; common author-defined ENU frame',
        'settling_seconds': 20,
        'interpolation_max_bracket_s': 1.0,
        'lever_arm_note': 'Author default GNSS zero lever arm retained; SPAN-to-IMU reference offset not compensated in this preliminary smoke check',
    }
    quality_rows = []
    for quality in np.unique(ref[valid, 19]):
        selected = ref[valid, 19] == quality
        quality_rows.append({
            'quality_flag': int(quality), 'epochs': int(selected.sum()),
            'rmse_horizontal_m': float(np.sqrt(np.mean(np.sum(error[selected, :2]**2, axis=1)))),
            'rmse_3d_m': float(np.sqrt(np.mean(error3[selected]**2))),
            'p95_3d_m': float(np.percentile(error3[selected], 95)),
            'max_3d_m': float(error3[selected].max()),
        })
    summary['reference_quality_metrics'] = quality_rows
    summary['reference_quality_note'] = 'Raw quality codes are preserved without assigning an unverified accuracy bound to each code.'
    (folder / (label + '_metrics.json')).write_text(json.dumps(summary, indent=2) + '\n')
    with (folder / (label + '_metrics.csv')).open('w', newline='') as stream:
        fields = ['sequence', 'mode', 'reference_epochs', 'rmse_horizontal_m', 'rmse_3d_m', 'p95_3d_m', 'max_3d_m']
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerow({key: summary[key] for key in fields})
    with (folder / (label + '_quality_metrics.csv')).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(quality_rows[0]))
        writer.writeheader()
        writer.writerows(quality_rows)
    with (folder / 'trajectory_enu.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['utc_s', 'east_m', 'north_m', 'up_m'])
        writer.writerows(result[:, [0,9,10,11]])
    for path in (ROOT / 'projects/GLIO_setup/fonts').glob('times*.ttf'):
        font_manager.fontManager.addfont(str(path))
    plt.rcParams.update({'font.family': 'Times New Roman', 'font.size': 10,
                         'axes.labelsize': 11, 'legend.fontsize': 9,
                         'pdf.fonttype': 42, 'ps.fonttype': 42})
    fig, ax = plt.subplots(figsize=(5.8, 4.0), layout='constrained')
    ax.plot(ref_enu[valid, 0], ref_enu[valid, 1], '--', color='0.15', lw=1.1, label='Reference')
    ax.plot(estimate[:, 0], estimate[:, 1], color='#0072B2', lw=1.1, label='GLIO ' + mode.replace('_', '-'))
    ax.set(xlabel='East (m)', ylabel='North (m)')
    ax.set_aspect('equal', adjustable='box')
    ax.grid(alpha=0.22, lw=0.5)
    ax.legend(frameon=False)
    for suffix in ['png', 'pdf']:
        fig.savefig(folder / (label + '_trajectory.' + suffix), dpi=300, bbox_inches='tight', pad_inches=0.05)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(5.8, 3.2), layout='constrained')
    ax.plot(rt-rt[0], error3, color='#0072B2', lw=1.0)
    ax.set(xlabel='Elapsed time (s)', ylabel='3D position error (m)')
    ax.grid(alpha=0.22, lw=0.5)
    for suffix in ['png', 'pdf']:
        fig.savefig(folder / (label + '_error.' + suffix), dpi=300, bbox_inches='tight', pad_inches=0.05)
    plt.close(fig)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
