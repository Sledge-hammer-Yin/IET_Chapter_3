#!/usr/bin/env bash
# Read-only progress display for the VS Code remote terminal.
python3 - <<'PY'
from pathlib import Path
root = Path('/data/users/taslab_zxp')
logs = root / 'outputs/GLIO/setup'
comparison = root / 'outputs/GLIO/Deep-Urban-1/Comparison_calibrated_v2'
if (comparison/'state.txt').exists():
    import json
    print('Controlled comparison:', (comparison/'state.txt').read_text().strip())
    if (comparison/'runs.json').exists():
        print('Validated full runs:', ', '.join(json.loads((comparison/'runs.json').read_text())))
    if (comparison/'comparison_metrics.csv').exists():
        print((comparison/'comparison_metrics.csv').read_text().strip())
    print('Comparison folder:', comparison)
state = logs / 'full_workflow.state'
print('Earlier single-run workflow:', state.read_text().strip() if state.exists() else 'not started')
exit_file = logs / 'full_workflow.exit'
if exit_file.exists():
    print('Workflow exit code:', exit_file.read_text().strip())
data = root / 'datasets/UrbanNav/Deep-Urban-1/rosbag'
sizes = {'UrbanNav-HK_Whampoa-20210521_sensors.z01':19327352832,
         'UrbanNav-HK_Whampoa-20210521_sensors.zip':18439651312}
actual = sum(min((data/name).stat().st_size, expected) if (data/name).exists() else 0 for name,expected in sizes.items())
expected = sum(sizes.values())
print('Archive download: {:.1f}% ({:.2f}/{:.2f} GB)'.format(100*actual/expected, actual/1e9, expected/1e9))
latest = root / 'projects/GLIO_setup/latest_run.txt'
if latest.exists():
    folder = Path(latest.read_text().strip())
    print('Latest run:', folder)
    for name in ['tc_sw_result.csv', 'tc_batch_result.csv', 'lc_result.csv']:
        path = folder/name
        if path.exists():
            print(name, 'rows:', sum(1 for line in path.open()))
    for name in ['smoke_metrics.csv', 'preliminary_metrics.csv']:
        path = folder/name
        if path.exists():
            print(path.read_text().strip())
PY
df -h /data/users/taslab_zxp
