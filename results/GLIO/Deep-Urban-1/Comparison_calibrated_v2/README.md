# Deep-Urban-1 controlled comparison

Completed modes: LC, TC-Pose, TC-Surface. All use the same calibrated-v2 profile,
shared inputs and initialization, fixed seed 42, and 1.0 replay rate.

Common evaluation epochs: 1514; common coverage:
99.87%. Evaluation is at the SPAN-CPT point with no
fitted trajectory or time alignment.

| Method | Horizontal RMSE (m) | 3D RMSE (m) | 3D P95 (m) |
|---|---:|---:|---:|
| LC | 3.590 | 5.912 | 8.522 |
| TC-Pose | 1.820 | 4.547 | 7.861 |
| TC-Surface | 1.622 | 3.508 | 5.622 |

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
