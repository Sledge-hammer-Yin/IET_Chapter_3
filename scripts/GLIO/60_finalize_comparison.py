"""Publish completed local experiment documentation without replacing raw results."""
import csv
import json
from pathlib import Path

root=Path('/data/users/taslab_zxp')
setup=root/'projects/GLIO_setup'
out=root/'outputs/GLIO/Deep-Urban-1/Comparison_calibrated_v2'
assert (out/'state.txt').read_text().strip()=='complete'
assert (out/'exit_code.txt').read_text().strip()=='0'
data=json.loads((out/'comparison_results.json').read_text())
assert len(data['metrics'])==3
assert len(set(data['gnss_frontend_position_sha256'].values()))==1
for row in data['metrics']:
    assert row['epochs']==data['common_reference_epochs']
    assert sum(r['epochs'] for r in data['reference_quality_metrics'] if r['method']==row['method'])==row['epochs']
fields=['method','horizontal_rmse_m','position_3d_rmse_m','position_3d_p95_m','position_3d_max_m']
with (out/'book_metrics.csv').open('w',newline='') as stream:
    writer=csv.DictWriter(stream,fieldnames=fields); writer.writeheader()
    for row in data['metrics']:
        writer.writerow({key:round(row[key],3) if isinstance(row[key],float) else row[key] for key in fields})
summary='\n'.join('| {method} | {horizontal_rmse_m:.3f} | {position_3d_rmse_m:.3f} | {position_3d_p95_m:.3f} |'.format(**row) for row in data['metrics'])
readme=f'''# Deep-Urban-1 controlled comparison

Completed modes: LC, TC-Pose, TC-Surface. All use the same calibrated-v2 profile,
shared inputs and initialization, fixed seed 42, and 1.0 replay rate.

Common evaluation epochs: {data['common_reference_epochs']}; common coverage:
{data['common_coverage_pct']:.2f}%. Evaluation is at the SPAN-CPT point with no
fitted trajectory or time alignment.

| Method | Horizontal RMSE (m) | 3D RMSE (m) | 3D P95 (m) |
|---|---:|---:|---:|
{summary}

Read [COMPARISON_REPORT.md](COMPARISON_REPORT.md) for the full results, figures,
coverage, raw reference-quality groups, resource observations and book insertion
text. Use `book_metrics.csv` for a compact chapter table. See
[IMPLEMENTATION_AUDIT.md](IMPLEMENTATION_AUDIT.md) for source corrections and
the frozen-attitude approximation; `source.patch` retains the exact code changes.

This is a qualified teaching case using a supplied initial prior and one ground
vehicle sequence. It is not exact reproduction of the GLIO paper's numerical
results, a statistical superiority test, or UAV flight validation.

Native runs are stored only once under `runs/`; `runs.json` records their paths.
The original and prepared datasets are shared and unchanged by the comparison.
'''
(out/'README.md').write_text(readme)
(setup/'LATEST_RESULTS.txt').write_text(str(out)+'\n')
(setup/'LATEST_COMPARISON.txt').write_text(str(out/'COMPARISON_REPORT.md')+'\n')

legacy=root/'outputs/GLIO/Deep-Urban-1/TC_Surface_20261105_121707/RUN_SUMMARY.md'
if legacy.exists():
    text=legacy.read_text()
    if not text.startswith('> Archived initial check'):
        legacy.write_text('> Archived initial check (author-v1 settings). The completed, corrected three-mode comparison is in [COMPARISON_REPORT.md](../Comparison_calibrated_v2/COMPARISON_REPORT.md). The historical numbers below are retained and excluded from the new table.\n\n'+text)
guide=setup/'README.md'
text=guide.read_text()
banner=f'''## Current completed comparison

The current controlled results are in `{out}`. All three modes completed the
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

'''
if '## Current completed comparison' not in text:
    heading,body=text.split('\n',1)
    updated=heading+'\n\n'+banner+body
    updated=updated.replace('The first verification retains the authors\' sequence-specific anchor and initial\nEuler angles. Their original derivation is not verified. Ground-truth measurements\nare excluded from online updates. The original zero GNSS lever arm is retained;\nits convention and the SPAN-to-IMU reference offset must be audited before a\nbook-quality accuracy comparison.',
        'The current comparison applies the published antenna translation and evaluates\nall methods at the SPAN reference point using estimated attitude. Shared supplied\ninitial priors are retained and their derivation is unverified. The exact changes\nand frozen adjacent-attitude approximation are documented in the comparison audit.\nThe earlier zero-lever-arm verification remains archived and is excluded from\nthe current statistics.')
    guide.write_text(updated)
check=setup/'SERVER_CHECK_20261105.txt'
with check.open('a') as stream:
    stream.write('\nSubsequent controlled comparison: all three modes completed under calibrated_v2.\n')
    stream.write('Common reference epochs: '+str(data['common_reference_epochs'])+'.\n')
    stream.write('Current report: '+str(out/'COMPARISON_REPORT.md')+'\n')
print('Completed report:',out/'COMPARISON_REPORT.md')
print('Compact book table:',out/'book_metrics.csv')
