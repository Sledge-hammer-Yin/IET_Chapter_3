#!/usr/bin/env bash
# Read-only checks; no sudo password, package installs, or service changes.
export LC_ALL=C
printf '\nIdentity and operating system\n'
id
hostname
cat /etc/os-release
printf '\nCPU and current load\n'
lscpu
nproc
uptime
printf '\nMemory\n'
free -h
printf '\nPersonal data directory and filesystems\n'
ls -ld /data/users/taslab_zxp
test -w /data/users/taslab_zxp && printf 'Personal data directory is writable\n'
df -hT /data/users/taslab_zxp /home/taslab_zxp
findmnt -T /data/users/taslab_zxp
du -sh /data/users/taslab_zxp
command -v quota >/dev/null && quota -s
find /data/users/taslab_zxp -mindepth 1 -maxdepth 2 -type d -print
printf '\nContainer and build tools\n'
for tool in docker podman apptainer singularity git cmake make gcc g++ python3 curl wget tmux unshare newuidmap newgidmap slirp4netns fuse-overlayfs; do
    command -v "$tool" || true
done
printf '\nDocker socket and permissions\n'
if command -v docker >/dev/null; then
    docker --version
    timeout 15 docker info --format '{{json .}}' 2>&1 | head -c 18000
fi
stat -c '%A %U %G %n' /var/run/docker.sock 2>/dev/null || true
printf '\nAvailable noninteractive sudo permissions\n'
sudo -n -l 2>&1 || true
printf '\nUser namespace availability\n'
cat /proc/sys/kernel/unprivileged_userns_clone /proc/sys/user/max_user_namespaces 2>/dev/null || true
unshare -Ur true 2>&1 && printf 'Unprivileged user namespace test passed\n'
printf '\nExisting ROS installations\n'
ls -ld /opt/ros /usr/local/bin/apptainer /usr/local/bin/singularity 2>/dev/null || true
printf '\nOwn active processes\n'
ps -u "$(id -u)" -o pid,pcpu,pmem,etime,comm --sort=-pcpu | head -n 12
