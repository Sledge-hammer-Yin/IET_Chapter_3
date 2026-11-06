#!/usr/bin/env bash
root=/data/users/taslab_zxp
printf '\nBuild status\n'
test ! -f "$root/outputs/GLIO/setup/build.exit" || cat "$root/outputs/GLIO/setup/build.exit"
tail -n 12 "$root/outputs/GLIO/setup/build.log"
printf '\nDownload progress\n'
find "$root/datasets/UrbanNav/Deep-Urban-1/rosbag" -maxdepth 1 -type f -printf '%s %f\n'
printf '\nPersonal disk use\n'
du -sh "$root"
printf '\nPrivate build/download processes\n'
ps -u "$(id -u)" -o pid,ppid,pcpu,pmem,etime,comm --sort=-pcpu | head -n 12
printf '\nOptional host evaluation libraries\n'
python3 - <<'PY'
import importlib.util
for module in ['numpy', 'matplotlib', 'scipy', 'yaml', 'venv']:
    print(module, importlib.util.find_spec(module) is not None)
PY
