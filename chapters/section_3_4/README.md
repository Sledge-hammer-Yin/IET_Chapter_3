# Section 3.4 Conventional positioning

| Group | Code | Configuration | Measured outputs |
|---|---|---|---|
| B1 to B3 | `algorithms/B1_ESKF`, `B2_ESKF_NIS`, `B3_GNSS_IMU_FGO` | `configs/benchmark.json` | `results/Deep-Urban-1`, `results/Medium-Urban-1`, `results/figures` |
| GLIO | `algorithms/GLIO` | `configs/GLIO/calibrated_v2` | `results/GLIO/Deep-Urban-1/Comparison_calibrated_v2` |

Paths in this table are relative to the repository root.
Read [B1 to B3 results](../../CHAPTER3_RESULTS.md) and
[GLIO results](../../results/GLIO/Deep-Urban-1/Comparison_calibrated_v2/COMPARISON_REPORT.md).
The groups are separate comparisons. GLIO uses LiDAR in addition to GNSS and IMU.
There are no trained weights for these classical estimators.

[Book insertion](BOOK_INSERTION.md) records the final figure numbers and text.
