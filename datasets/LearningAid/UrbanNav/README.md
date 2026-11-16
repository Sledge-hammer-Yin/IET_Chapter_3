# UrbanNav GNSS test inputs

Source: https://github.com/IPNL-POLYU/UrbanNavDataset/tree/master/UrbanNav-HK-Deep-Urban-1

Use Deep-Urban-1 for testing only. Download the rover RINEX observations,
navigation file and SPAN reference. Reuse the existing server files when available.
The original filename contains `medium-urban.whampoa`; keep this filename.

```text
$CH3_ROOT/datasets/UrbanNav/Deep-Urban-1/
  gnss/20210521.medium-urban.whampoa.ublox.f9p.obs
  gnss/hksc141g.nav
  ground_truth/UrbanNav_whampoa_raw.txt
```

`prepare_gnss.py` applies the recorded reference-point conversion and writes
features to `$CH3_ROOT/datasets/UrbanNav/learning_processed`. KLT provides the
training and validation inputs. From the repository root run
`python scripts/LearningAid/run.py gnss --output NEW_RESULTS --models MODEL_DIR`.
Use a new model directory to retrain, or the downloaded model directory to reuse weights.
No camera, LiDAR or ROS bag data are needed. Reference quality varies along this
vehicle sequence. The Q=1 subset is a diagnostic, not a model-selection set.
