# UTIL UWB and inertial inputs

Source: https://github.com/learnsyslab/util-uwb-dataset
Dataset page: https://utiasdsl.github.io/util-uwb-dataset/
Release: https://github.com/learnsyslab/util-uwb-dataset/releases/tag/dataset-v1.0

Extract the flight CSV files and surveyed anchor positions. Keep the release layout:

```text
$CH3_ROOT/datasets/UTIL/dataset/flight-dataset/
  csv-data/const1/const1-trial{1,2,3}-tdoa2.csv
  csv-data/const2/const2-trial{1,2,3}-tdoa2.csv
  csv-data/const3/const3-trial{1,2,3}-tdoa2.csv
  csv-data/const4/const4-trial{1,2,3}-tdoa2-traj{1,2,3}.csv
  survey-results/anchor_const{1,2,3,4}.npz
```

Braces above denote separate files. Train on const1-2, validate on const3,
and test on all nine const4 recordings. `run_uwb.py` reads the CSV and anchor
files directly. It uses IMU and TDoA2 measurements, not CIR or static NLOS labels.
From the repository root run
`python scripts/LearningAid/run.py uwb --output NEW_RESULTS --models MODEL_DIR`.
Complete ROS bags and the static identification dataset are not required.
