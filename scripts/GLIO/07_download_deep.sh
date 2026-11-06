#!/usr/bin/env bash
set -euo pipefail
umask 077
root=/data/users/taslab_zxp
data_dir="$root/datasets/UrbanNav/Deep-Urban-1/rosbag"
mkdir -p "$data_dir"
exec 9>"$data_dir/download.lock"
flock -n 9 || { printf 'Download already running\n'; exit 0; }
cd "$data_dir"
download() {
    url="$1"
    name="$2"
    if [ -f "$name.complete" ]; then
        printf 'Already complete: %s\n' "$name"
        return
    fi
    printf 'Downloading %s at %s\n' "$name" "$(date -Is)"
    curl --fail --location --continue-at - --retry 8 --retry-delay 15 --connect-timeout 20 --limit-rate 35M --output "$name" "$url"
    sha256sum "$name" > "$name.sha256"
    touch "$name.complete"
}
download 'https://www.dropbox.com/scl/fo/jlzq9mvpdco4i6dqx4t6k/AMcl1SSsLdNQOsrbYxn9kWs/uncompress.txt?rlkey=579a2yhnei9xgehs42lg89ykr&dl=1' uncompress.txt
cat uncompress.txt
download 'https://www.dropbox.com/scl/fo/jlzq9mvpdco4i6dqx4t6k/AFXGRwOmjU9EaxyaBHudTuU/UrbanNav-HK_Whampoa-20210521_sensors.z01?rlkey=579a2yhnei9xgehs42lg89ykr&dl=1' UrbanNav-HK_Whampoa-20210521_sensors.z01
download 'https://www.dropbox.com/scl/fo/jlzq9mvpdco4i6dqx4t6k/ALmnCH-p5XZOexk8I983Mkg/UrbanNav-HK_Whampoa-20210521_sensors.zip?rlkey=579a2yhnei9xgehs42lg89ykr&dl=1' UrbanNav-HK_Whampoa-20210521_sensors.zip
printf 'All archive parts downloaded at %s\n' "$(date -Is)"
