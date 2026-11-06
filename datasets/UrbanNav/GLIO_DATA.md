# UrbanNav data for GLIO

Official source:
https://github.com/IPNL-POLYU/UrbanNavDataset
https://github.com/IPNL-POLYU/UrbanNavDataset/tree/master/UrbanNav-HK-Deep-Urban-1

Do not commit datasets. Download and process the full data on the Ubuntu server.
Current data root:
/data/users/taslab_zxp/datasets/UrbanNav/Deep-Urban-1

Inputs used by all three modes:
- processed/Deep-Urban-1_GLIO_input.bag: IMU, center LiDAR and time reference.
- gnss/20210521.medium-urban.whampoa.ublox.f9p.obs: rover observations.
- gnss/hksc1410.21o: base observations.
- gnss/hksc141g.nav: navigation data.
- calibration/: published sensor extrinsics and IMU calibration.

Reference, for offline evaluation only:
ground_truth/UrbanNav_whampoa_raw.txt

The original bag is retained under rosbag/.
The prepared bag removes only the first LiDAR scan preceding the first IMU.
For a fresh preparation, see 35_prepare_glio_input.py and 36_prepare_input.sh
in scripts/GLIO and the archived server setup.

Existing-server example:
bash /data/users/taslab_zxp/projects/GLIO_setup/13_run_deep.sh LC 0 /data/users/taslab_zxp/datasets/UrbanNav/Deep-Urban-1/processed/Deep-Urban-1_GLIO_input.bag 1.0

Replace LC with TC_Pose or TC_Surface for the other modes.
See algorithms/GLIO/RUN_SERVER.md for setup and run details.
The completed comparison contains its exact protocol and evaluation epochs.
B1-B3 retain their existing data and run instructions.
