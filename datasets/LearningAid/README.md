# Data for Section 3.5

This directory contains instructions and small provenance manifests only.
No raw sensor dataset is included. Download inputs to the runtime base selected
by `CH3_ROOT`, outside the Git repository. The adapters expect
`$CH3_ROOT/datasets/<dataset>/...`. The default local runtime base is the sibling
`data/LearningAid` directory. Keep references separate from sensor inputs.

| Guide | Role |
|---|---|
| [UrbanNav](UrbanNav/README.md) | Held-out GNSS evaluation |
| [KLT](KLT/README.md) | GNSS training and validation |
| [UTIL](UTIL/README.md) | UWB/inertial training, validation and evaluation |
| [EuRoC](EuRoC/README.md) | Inertial odometry training, validation and evaluation |

The sequence lists and seeds are fixed in
`../../configs/LearningAid/protocol.json`. Paths in the recorded manifests refer
to the original server run. Use the paths in these guides for a new setup.
Do not download camera images, point clouds or complete ROS bags for these tests.
