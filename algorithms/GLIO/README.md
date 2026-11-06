# GLIO three-mode comparison

LC, TC-Pose and TC-Surface share one GLIO implementation. No trained models or
model weights are required. Configurations are in `configs/GLIO/calibrated_v2`
from the main repository root. Outputs and plots are in
`results/GLIO/Deep-Urban-1/Comparison_calibrated_v2`.

LC uses gated GNSS position factors. TC-Pose uses DD pseudorange with relative
pose constraints. TC-Surface uses DD pseudorange with LiDAR surface constraints.
The active shared front end is LiDAR/IMU; Doppler factors are disabled here.
Read the result report and implementation audit for initialization, lever-arm
approximation, common epochs and reference-quality limits.

## Source

Upstream: https://github.com/XikunLiu-huskit/GLIO
Base revision: `332d19ff641f2ada9d9d75f2a6dab013d6015f76`.
The exact local estimator patch is `source.patch`; its hash is in `source_lock.json`.
From the main repository root, run:

```powershell
python algorithms/GLIO/fetch_upstream.py
```

This fetches code into the sibling `external/GLIO` folder and applies the checked
patch. Third-party source and its original comments are not included in the
English-only manual upload export. Keep upstream notices and licenses.
The original local submodule and complete workspace archive remain available
as private backups. Do not upload their internal Git directories or binaries.

## Existing server

Use VS Code Remote-SSH and the existing personal server directory.
For example, in the remote Ubuntu terminal:

```bash
task_root=/data/users/taslab_zxp
input_bag="$task_root/datasets/UrbanNav/Deep-Urban-1/processed/Deep-Urban-1_GLIO_input.bag"
bash "$task_root/projects/GLIO_setup/13_run_deep.sh" LC 0 "$input_bag" 1.0
```

Replace `LC` with `TC_Pose` or `TC_Surface`. This creates a new native run; it
does not replace the archived three-mode table. Do not rerun the old comparison
wrapper into the frozen result directory. A fresh comparison needs a new output
root and one shared, predeclared evaluation protocol.

See [the retained server guide](RUN_SERVER.md) for its original paths.
The copied server scripts retain those paths; they are not Windows launchers.
`evaluation/GLIO/compare_modes.py` documents the completed offline comparison.
Its existing server evaluation root is fixed, so do not use it for new runs
without deliberately assigning a new matching protocol and runs manifest.
