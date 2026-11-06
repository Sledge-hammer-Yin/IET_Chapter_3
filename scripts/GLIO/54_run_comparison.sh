#!/usr/bin/env bash
set -euo pipefail
umask 077
root=/data/users/taslab_zxp
setup_dir="$root/projects/GLIO_setup"
out="$root/outputs/GLIO/Deep-Urban-1/Comparison_calibrated_v2"
mkdir -p "$out/runs"
exec 8>"$out/workflow.lock"
flock -n 8 || { printf 'Comparison already running\n'; exit 3; }
export GLIO_PROFILE_DIR="$setup_dir/profiles/calibrated_v2"
export GLIO_RUN_ROOT="$out/runs"
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=4
for mode in LC TC_Pose TC_Surface; do
    printf 'running_%s\n' "$mode" > "$out/state.txt"
    python3 "$setup_dir/check_frozen_protocol.py"
    started="$(date +%s.%N)"
    bash "$setup_dir/13_run_deep.sh" "$mode" 0 "$root/datasets/UrbanNav/Deep-Urban-1/processed/Deep-Urban-1_GLIO_input.bag" 1.0
    ended="$(date +%s.%N)"
    run_dir="$(cat "$setup_dir/latest_run.txt")"
    python3 "$setup_dir/validate_comparison_run.py" "$run_dir" "$mode"
    python3 "$setup_dir/check_frozen_protocol.py"
    python3 - "$out" "$mode" "$run_dir" "$started" "$ended" <<'PY'
import json,sys
from pathlib import Path
folder=Path(sys.argv[1]); path=folder/'runs.json'
runs=json.loads(path.read_text()) if path.exists() else {}
runs[sys.argv[2]]={'path':sys.argv[3],'wall_start_unix':float(sys.argv[4]),'wall_end_unix':float(sys.argv[5]),'end_to_end_wall_s':float(sys.argv[5])-float(sys.argv[4])}
temporary=path.with_suffix('.tmp'); temporary.write_text(json.dumps(runs,indent=2)+'\n'); temporary.replace(path)
PY
done
printf 'evaluating\n' > "$out/state.txt"
export XDG_CACHE_HOME="$root/installers/cache"
export MPLCONFIGDIR="$root/installers/cache/matplotlib"
nice -n 10 taskset -c 0-3 "$root/envs/glio_eval/bin/python" "$setup_dir/compare_modes.py"
printf 'complete\n' > "$out/state.txt"
