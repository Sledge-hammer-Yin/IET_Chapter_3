#!/usr/bin/env bash
set -euo pipefail
root=/data/users/taslab_zxp
export APPTAINER_CACHEDIR="$root/installers/apptainer/cache"
export APPTAINER_TMPDIR="$root/installers/apptainer/tmp"
export TMPDIR="$APPTAINER_TMPDIR"
nice -n 10 taskset -c 0-3 apptainer exec --cleanenv --no-home --bind "$root:$root" "$root/installers/apptainer/images/glio-melodic.sif" bash -c '
    set -e
    source /opt/ros/melodic/setup.bash
    python /data/users/taslab_zxp/projects/GLIO_setup/35_prepare_glio_input.py
    rosbag info /data/users/taslab_zxp/datasets/UrbanNav/Deep-Urban-1/processed/Deep-Urban-1_GLIO_input.bag
'
