#!/usr/bin/env bash
set -euo pipefail
umask 077
root=/data/users/taslab_zxp
data_dir="$root/datasets/UrbanNav/Deep-Urban-1/rosbag"
export APPTAINER_CACHEDIR="$root/installers/apptainer/cache"
export APPTAINER_TMPDIR="$root/installers/apptainer/tmp"
export TMPDIR="$APPTAINER_TMPDIR"
exec 9>"$data_dir/extract.lock"
flock -n 9 || { printf 'Extraction already active\n'; exit 0; }
test -f "$data_dir/UrbanNav-HK_Whampoa-20210521_sensors.z01.complete"
test -f "$data_dir/UrbanNav-HK_Whampoa-20210521_sensors.zip.complete"
test "$(stat -c %s "$data_dir/UrbanNav-HK_Whampoa-20210521_sensors.z01")" = 19327352832
test "$(stat -c %s "$data_dir/UrbanNav-HK_Whampoa-20210521_sensors.zip")" = 18439651312
if [ -f "$data_dir/extraction.complete" ]; then
    printf 'Previously validated extraction exists\n'
    exit 0
fi
test ! -f "$data_dir/UrbanNav-HK_Whampoa-20210521_sensors.bag"
nice -n 10 taskset -c 0-3 apptainer exec --cleanenv --no-home --bind "$root:$root" "$root/installers/apptainer/images/glio-melodic.sif" bash -c '
    set -e
    cd "$1"
    7z x -bd -bb0 UrbanNav-HK_Whampoa-20210521_sensors.zip
    source /opt/ros/melodic/setup.bash
    rosbag info --yaml UrbanNav-HK_Whampoa-20210521_sensors.bag > source_bag_info.yaml
' _ "$data_dir"
touch "$data_dir/extraction.complete"
printf 'Full dataset extracted and archive CRC checked\n'
