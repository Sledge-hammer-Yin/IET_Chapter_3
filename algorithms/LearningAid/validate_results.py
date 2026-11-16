"""Check the saved trajectories and tables without raw datasets or trained models."""
import csv
import json
from pathlib import Path
import numpy as np
from common import OUT, metrics, relative_error_vectors


def validate():
    t = np.arange(31.)
    zero = np.zeros((31, 3))
    assert metrics(np.ones((31, 3)), zero, t)['rpe_10s_m'] == 0
    drift = np.column_stack((t, t * 0, t * 0))
    assert np.isclose(metrics(drift, zero, t)['rpe_10s_m'], 10.)
    expected = {'GNSS': 10, 'UWB': 72, 'IO': 40}
    totals = {}
    for group, count in expected.items():
        rows = list(csv.DictReader((OUT / group / 'metrics.csv').open(encoding='utf-8')))
        assert len(rows) == count, (group, len(rows))
        errors, relative = {}, {}
        for row in rows:
            path = OUT / group / f'{row["sequence"]}_{row["method"]}_{row["seed"]}.npz'
            with np.load(path, allow_pickle=False) as saved:
                p, g, ts = saved['position'], saved['reference'], saved['time']
                assert p.shape == g.shape == (len(ts), 3)
                assert np.isfinite(p).all() and np.isfinite(g).all()
                assert np.isfinite(ts).all() and np.all(np.diff(ts) > 0)
                score = metrics(p, g, ts)
                for key in ('rmse_3d_m', 'rmse_horizontal_m', 'p95_3d_m', 'rpe_10s_m'):
                    assert np.isclose(score[key], float(row[key]), rtol=1e-9, atol=1e-9), (path.name, key)
                key = (row['method'], int(row['seed']))
                errors.setdefault(key, []).append(p - g)
                relative.setdefault(key, []).append(relative_error_vectors(p, g, ts))
        per_seed = {}
        for key, parts in errors.items():
            e = np.concatenate(parts)
            r = np.linalg.norm(e, axis=1)
            rel = np.concatenate(relative[key])
            per_seed[key] = {
                'rmse_3d_m': np.sqrt(np.mean(r ** 2)),
                'rmse_horizontal_m': np.sqrt(np.mean(np.sum(e[:, :2] ** 2, axis=1))),
                'p95_3d_m': np.percentile(r, 95),
                'rpe_10s_m': np.sqrt(np.mean(np.sum(rel ** 2, axis=1))),
                'samples': len(e),
            }
        summaries = list(csv.DictReader((OUT / group / 'summary.csv').open(encoding='utf-8')))
        assert {x['method'] for x in summaries} == {key[0] for key in per_seed}
        for row in summaries:
            selected = [v for (method, _), v in per_seed.items() if method == row['method']]
            assert len(selected) == int(row['training_seeds'])
            assert all(v['samples'] == int(row['samples_per_seed']) for v in selected)
            for key in ('rmse_3d_m', 'rmse_horizontal_m', 'p95_3d_m', 'rpe_10s_m'):
                values = [v[key] for v in selected]
                for suffix, value in [('mean', np.mean(values)), ('std', np.std(values, ddof=1) if len(values) > 1 else 0.)]:
                    assert np.isclose(value, float(row[f'{key}_{suffix}']), rtol=1e-9, atol=1e-9), (group, row['method'], key, suffix)
        totals[group] = count
    print(json.dumps({'status': 'passed', 'saved_evaluations': totals, 'raw_datasets_required': False}, indent=2))


if __name__ == '__main__':
    validate()
