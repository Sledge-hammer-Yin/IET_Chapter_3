#!/usr/bin/env bash
set -euo pipefail
root=/data/users/taslab_zxp
export APPTAINER_CACHEDIR="$root/installers/apptainer/cache"
export APPTAINER_TMPDIR="$root/installers/apptainer/tmp"
export TMPDIR="$APPTAINER_TMPDIR"
bag="$root/datasets/UrbanNav/Deep-Urban-1/processed/Deep-Urban-1_smoke_prefix.bag"
nice -n 10 taskset -c 0-3 apptainer exec --cleanenv --no-home --bind "$root:$root" "$root/installers/apptainer/images/glio-melodic.sif" bash -c '
    set -e
    source /opt/ros/melodic/setup.bash
    rosbag reindex "$1"
    rosbag info "$1"
' _ "$bag"
