#!/usr/bin/env bash
set -euo pipefail
root=/data/users/taslab_zxp
export APPTAINER_CACHEDIR="$root/installers/apptainer/cache"
export APPTAINER_TMPDIR="$root/installers/apptainer/tmp"
export TMPDIR="$APPTAINER_TMPDIR"
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=1
image="$root/installers/apptainer/images/glio-melodic.sif"
workspace="$root/projects/GLIO_ws"
test -f "$image"
nice -n 10 taskset -c 0-3 apptainer exec --cleanenv --no-home \
    --bind "$root:$root" "$image" bash -c '
        set -e
        source /opt/ros/melodic/setup.bash
        cd /data/users/taslab_zxp/projects/GLIO_ws
        catkin_make -j4 -l4 -DCATKIN_BLACKLIST_PACKAGES=rviz_satellite
    '
test -x "$workspace/devel/lib/GLIO/Estimator"
test -x "$workspace/devel/lib/GLIO/Preprocessing"
test -x "$workspace/devel/lib/GLIO/LidarOdometry"
test -x "$workspace/devel/lib/global_fusion/gnss_preprocessor_node"
printf 'GLIO executable checks passed\n'
