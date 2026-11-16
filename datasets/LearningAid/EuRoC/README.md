# EuRoC inertial inputs

Original dataset: https://projects.asl.ethz.ch/datasets/euroc-mav/
IMU-only release used here: https://github.com/Air-IO/Air-IO/releases/tag/datasets

Use the AirIO IMU-only release to match the recorded reference version.
Keep only IMU CSV, state-reference CSV and sensor metadata for the 11 sequences.
Camera images are not needed. Preserve the original sequence folder names:

```text
$CH3_ROOT/datasets/EuRoC/<sequence>/mav0/
  imu0/data.csv
  state_groundtruth_estimate0/data.csv
```

- Train: MH_01_easy, MH_05_difficult, V1_02_medium, V2_01_easy, V2_03_difficult.
- Validation: MH_03_medium.
- Test: MH_02_easy, MH_04_difficult, V1_01_easy, V1_03_difficult, V2_02_medium.

For `V1_01_easy`, also place the corrected reference at
`mav0/state_groundtruth_estimate0/data_openvins.csv`. Use the corrected reference
distributed with AirIO. Alternatively place the original correction archive at
`$CH3_ROOT/tmp/Chapter3_3.5/V101-reference.zip`; the adapter reads
`V101-state_groundtruth_estimate0/data.csv` from that archive.

`prepare_io.py` produces separate `inputs.npz` and `reference.npz` files under
`$CH3_ROOT/datasets/EuRoC/processed_learning`. From the repository root run
`python scripts/LearningAid/run.py io --output NEW_RESULTS --models MODEL_DIR`.
Inference uses a shared initial reference state, then estimated attitude and IMU only.
