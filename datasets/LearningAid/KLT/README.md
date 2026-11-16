# KLT GNSS training and validation inputs

Source and download instructions: https://github.com/ebhrz/KLTDataset

Download the June 10, 2021 GNSS files and reference data, without the ROS bags.
Use the download links maintained in the upstream README.

```text
$CH3_ROOT/datasets/KLT/0610_KLT/
  COM38_210610_025603.obs
  20210610_100.txt
  sta/hksc161d.21*
```

Train on `0610_KLT1_203` and `0610_KLT2_209`. Validate on `0610_KLT3_404`.
`prepare_gnss.py` selects the fixed time intervals recorded in its entry point.
Features are stored in `$CH3_ROOT/datasets/UrbanNav/learning_processed` alongside
the separately prepared UrbanNav test features. Keep the original file names.
Run the GNSS command in the UrbanNav guide after preparing both datasets.
