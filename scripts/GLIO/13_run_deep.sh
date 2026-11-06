#!/usr/bin/env bash
set -euo pipefail
umask 077
root=/data/users/taslab_zxp
mode="${1:-TC_Surface}"
duration="${2:-120}"
rate="${4:-0.5}"
case "$mode" in LC|TC_Pose|TC_Surface) ;; *) printf 'Mode must be LC, TC_Pose, or TC_Surface\n'; exit 2;; esac
case "$duration" in ''|*[!0-9]*) printf 'Duration must be an integer number of seconds (0 = full sequence)\n'; exit 2;; esac
setup_dir="$root/projects/GLIO_setup"
profile_dir="${GLIO_PROFILE_DIR:-$setup_dir/profiles/calibrated_v2}"
config_dir="$profile_dir/configs"
image="$root/installers/apptainer/images/glio-melodic.sif"
bag="${3:-$root/datasets/UrbanNav/Deep-Urban-1/processed/Deep-Urban-1_GLIO_input.bag}"
test -f "$bag"
test -x "$root/projects/GLIO_ws/devel/lib/GLIO/Estimator"
run_root="${GLIO_RUN_ROOT:-$root/outputs/GLIO/Deep-Urban-1}"
run_dir="$run_root/${mode}_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$run_dir/ros_logs" "$run_dir/ros_home"
exec 9>"$setup_dir/run.lock"
flock -n 9 || { printf 'Another private GLIO run is active\n'; exit 3; }
if ss -H -ltn 'sport = :11371' | grep -q .; then
    printf 'Port 11371 is occupied; refusing to interfere\n'
    exit 4
fi
export APPTAINER_CACHEDIR="$root/installers/apptainer/cache"
export APPTAINER_TMPDIR="$root/installers/apptainer/tmp"
export TMPDIR="$APPTAINER_TMPDIR"
# Bound each solver process to 24 GiB of virtual memory.
ulimit -v 25165824
cp "$config_dir/$mode.yaml" "$run_dir/config.yaml"
cp "$profile_dir/manifest.json" "$run_dir/manifest.json"
printf '%s\n' "$duration" > "$run_dir/requested_duration_seconds.txt"
printf '%s\n' "$bag" > "$run_dir/source_bag_path.txt"
printf '%s\n' "$rate" > "$run_dir/playback_rate.txt"
printf '%s\n' "$run_dir" > "$setup_dir/latest_run.txt"
cd "$root"
nice -n 10 taskset -c 0-3 apptainer exec --cleanenv --no-home \
    --env ROS_MASTER_URI=http://127.0.0.1:11371 \
    --env ROS_IP=127.0.0.1 --env ROS_HOSTNAME=127.0.0.1 \
    --env OMP_NUM_THREADS=4 --env OPENBLAS_NUM_THREADS=1 \
    --env GLIO_RANDOM_SEED=42 \
    --env ROS_LOG_DIR="$run_dir/ros_logs" \
    --env ROS_HOME="$run_dir/ros_home" \
    --bind "$root:$root" "$image" bash -s -- "$mode" "$duration" "$run_dir" "$bag" "$rate" "$config_dir/$mode.launch" <<'INNER'
set -euo pipefail
mode="$1"
duration="$2"
run_dir="$3"
bag="$4"
rate="$5"
launch_file="$6"
set +u
source /opt/ros/melodic/setup.bash
source /data/users/taslab_zxp/projects/GLIO_ws/devel/setup.bash
set -u
launch_pid=''
playback_pid=''
sampler_pid=''
cleanup() {
    rc=$?
    trap - EXIT
    if [ -n "$playback_pid" ] && kill -0 "$playback_pid" 2>/dev/null; then
        kill -INT -- "-$playback_pid" 2>/dev/null || true
        wait "$playback_pid" || true
    fi
    if [ -n "$launch_pid" ] && kill -0 "$launch_pid" 2>/dev/null; then
        kill -INT "$launch_pid" 2>/dev/null || true
        wait "$launch_pid" || true
    fi
    if [ -n "$sampler_pid" ]; then wait "$sampler_pid" || true; fi
    exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
roslaunch -p 11371 "$launch_file" result_dir:="$run_dir" > "$run_dir/launch.log" 2>&1 &
launch_pid="$!"
python3 /data/users/taslab_zxp/projects/GLIO_setup/sample_resources.py "$launch_pid" "$run_dir" > "$run_dir/resource_sampler.log" 2>&1 &
sampler_pid="$!"
# Wait for GNSS preprocessing and solver initialization before playing the bag.
sleep 15
kill -0 "$launch_pid"
if grep -qE 'REQUIRED process.*has died|Check failed:' "$run_dir/launch.log"; then exit 20; fi
args=(--quiet --rate "$rate" --queue 2000)
if [ "$duration" -gt 0 ]; then args+=(--duration "$duration"); fi
date -Is > "$run_dir/playback_started.txt"
setsid /usr/bin/time -v -o "$run_dir/playback_time.txt" rosbag play "${args[@]}" "$bag" --topics /velodyne_points /imu/data /time_reference > "$run_dir/playback.log" 2>&1 &
playback_pid="$!"
while kill -0 "$playback_pid" 2>/dev/null; do
    if ! kill -0 "$launch_pid" 2>/dev/null || grep -qE 'REQUIRED process.*has died|Check failed:' "$run_dir/launch.log"; then
        printf 'A required GLIO node failed; stopping playback\n'
        exit 21
    fi
    sleep 2
done
wait "$playback_pid"
playback_pid=''
date -Is > "$run_dir/playback_finished.txt"
python3 /data/users/taslab_zxp/projects/GLIO_setup/wait_backend.py "$run_dir" --mode "$mode"
kill -0 "$launch_pid"
case "$mode" in LC) expected=lc_result.csv;; *) expected=tc_batch_result.csv;; esac
test -s "$run_dir/$expected"
printf 'Expected output rows: '; wc -l "$run_dir/$expected"
printf 'RUN_OUTPUT=%s\n' "$run_dir"
INNER
case "$mode" in LC) expected=lc_result.csv;; *) expected=tc_batch_result.csv;; esac
if [ ! -s "$run_dir/$expected" ]; then
    printf 'Missing expected trajectory: %s\n' "$run_dir/$expected"
    exit 22
fi
