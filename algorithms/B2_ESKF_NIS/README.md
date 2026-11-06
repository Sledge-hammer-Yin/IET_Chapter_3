# B2_ESKF_NIS

The same ESKF with NIS observation rejection. No model training or weights are required.
Use `configs/benchmark.json`. From the main project folder in PowerShell:

```powershell
.\run_benchmark.ps1 -Action run -Sequence Deep-Urban-1 -Method B2_ESKF_NIS
```

Use `Medium-Urban-1` for the second sequence. After rerunning methods, regenerate
the shared metrics and figures with `-Action summarize` and `-Action plot`.
Saved outputs are under `results/<sequence>/`; figures are under `results/figures/`.
See the main README, METHODS.md and datasets/README.md for setup and assumptions.
