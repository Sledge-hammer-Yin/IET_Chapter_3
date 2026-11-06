#!/usr/bin/env bash
set -euo pipefail
umask 077
root=/data/users/taslab_zxp
setup_dir="$root/projects/GLIO_setup"
data_dir="$root/datasets/UrbanNav/Deep-Urban-1/rosbag"
log_dir="$root/outputs/GLIO/setup"
exec 8>"$setup_dir/full_workflow.lock"
flock -n 8 || { printf 'Full workflow already active\n'; exit 0; }
printf 'waiting_for_download\n' > "$log_dir/full_workflow.state"
deadline=$((SECONDS+10800))
while [ ! -f "$data_dir/UrbanNav-HK_Whampoa-20210521_sensors.zip.complete" ]; do
    if [ "$SECONDS" -gt "$deadline" ]; then printf 'Download wait expired\n'; exit 10; fi
    download_pid="$(cat "$log_dir/download.pid")"
    status="$(ps -p "$download_pid" -o stat= || true)"
    if [ -z "$status" ] || [[ "$status" == Z* ]]; then
        printf 'Download process stopped before completion\n'; exit 11
    fi
    sleep 20
done
printf 'extracting_and_checking_archive\n' > "$log_dir/full_workflow.state"
bash "$setup_dir/26_extract_full.sh"
printf 'running_full_TC_Surface\n' > "$log_dir/full_workflow.state"
bash "$setup_dir/13_run_deep.sh" TC_Surface 0 "$root/datasets/UrbanNav/Deep-Urban-1/processed/Deep-Urban-1_GLIO_input.bag" 1.0
run_dir="$(cat "$setup_dir/latest_run.txt")"
printf 'evaluating_full_TC_Surface\n' > "$log_dir/full_workflow.state"
export XDG_CACHE_HOME="$root/installers/cache"
export MPLCONFIGDIR="$root/installers/cache/matplotlib"
"$root/envs/glio_eval/bin/python" "$setup_dir/19_evaluate_smoke.py" "$run_dir"
printf '%s\n' "$run_dir" > "$log_dir/full_run_output.txt"
printf 'complete\n' > "$log_dir/full_workflow.state"
