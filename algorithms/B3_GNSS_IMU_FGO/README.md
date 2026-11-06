# B3_GNSS_IMU_FGO

GNSS/IMU fixed-lag factor graph with IMU preintegration. No model training or weights are required.
Use `configs/benchmark.json`. From the main project folder in PowerShell:

```powershell
.\run_benchmark.ps1 -Action run -Sequence Deep-Urban-1 -Method B3_GNSS_IMU_FGO
```

Use `Medium-Urban-1` for the second sequence. After rerunning methods, regenerate
the shared metrics and figures with `-Action summarize` and `-Action plot`.
Saved outputs are under `results/<sequence>/`; figures are under `results/figures/`.
See the main README, METHODS.md and datasets/README.md for setup and assumptions.
