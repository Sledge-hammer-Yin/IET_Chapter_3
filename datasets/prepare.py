"""Convert local UrbanNav exports without copying or changing raw files."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import numpy as np
import pandas as pd
from algorithms.common import lla_ecef, ecef_frame

SEQUENCES = {
    "Deep-Urban-1": {
        "imu": "imu/xsense_imu_deep_urban1.csv",
        "reference": "ground_truth/UrbanNav_whampoa_raw.txt",
        "rover": "gnss/20210521.medium-urban.whampoa.ublox.f9p.obs.txt",
        "base": "gnss/hksc1410.21o.txt", "nav": "gnss/hksc141g.nav.txt"},
    "Medium-Urban-1": {
        "imu": "imu/xsense_imu_medium_urban1.csv",
        "reference": "ground_truth/UrbanNav_TST_GT_raw.txt",
        "rover": "gnss/UrbanNav-HK-Medium-Urban-1.ublox.f9p.splitter.obs",
        "base": "gnss/hksc137c.21o", "nav": "gnss/hksc137c.nav"}}


def preparation_settings(cfg):
    return {k: cfg[k] for k in ["imu_rate_hz", "dgnss_sigma_floor_m",
                               "spp_sigma_floor_m", "base_ecef_m",
                               "gnss_constellation", "gnss_frontend", "rtklib_navsys_mask"]}


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(2**20), b""):
            h.update(block)
    return h.hexdigest()


def run_frontend(root, paths, dest, cfg):
    commands = {}
    # The 2.4.3 b34 -sys switch falls through its C cases. Use an explicit
    # configuration mask instead of relying on that command-line option.
    options = dest/"rtklib.conf"
    options_text = f"pos1-navsys = {cfg['rtklib_navsys_mask']}\nout-outopt = on\n"
    options.write_text(options_text, encoding="ascii")
    binary_sha = digest(root/"external/RTKLIB_bin/rnx2rtkp.exe")
    command_file = dest/"gnss_command.json"
    previous = json.loads(command_file.read_text()) if command_file.exists() else {}
    for name, mode in [("dgnss", "1"), ("spp", "0")]:
        output = dest/f"gnss_{name}.pos"
        cmd = [str(root/"external/RTKLIB_bin/rnx2rtkp.exe"), "-k", str(options), "-p", mode,
               "-m", "15", "-e", "-t", "-u"]
        if mode == "1":
            cmd += ["-f", "1", "-r"]+list(map(str, cfg["base_ecef_m"]))
        cmd += ["-o", str(output), str(paths["rover"])]
        if mode == "1":
            cmd.append(str(paths["base"]))
        cmd.append(str(paths["nav"]))
        commands[name] = cmd
        if (not output.exists() or previous.get(name) != cmd
                or previous.get("options") != options_text
                or previous.get("binary_sha256") != binary_sha):
            completed = subprocess.run(cmd, capture_output=True, text=True)
            if completed.returncode or not output.exists():
                raise RuntimeError(completed.stderr[-2000:])
    commands.update(binary_sha256=binary_sha, options=options_text)
    command_file.write_text(json.dumps(commands, indent=2), encoding="utf-8")


def read_positions(path):
    rows = {}
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith("%"):
            continue
        fields = line.split()
        t = datetime.strptime(" ".join(fields[:2]), "%Y/%m/%d %H:%M:%S.%f").replace(
            tzinfo=timezone.utc).timestamp()
        v = np.array(list(map(float, fields[2:])))
        if abs(t-round(t)) > .002:
            raise ValueError("The benchmark expects 1 Hz GNSS epochs.")
        s = v[5:8]
        xy, yz, zx = np.sign(v[8:11])*v[8:11]**2
        cov = np.diag(s*s)
        cov[0, 1] = cov[1, 0] = xy
        cov[1, 2] = cov[2, 1] = yz
        cov[0, 2] = cov[2, 0] = zx
        rows[int(round(t))] = (v[:3], cov, int(v[3]), int(v[4]))
    return rows


def read_imu(path, rate):
    names = ["field.header.stamp"]+[f"field.{q}.{a}" for q in
             ["angular_velocity", "linear_acceleration"] for a in "xyz"]
    arrays = []
    stamps = []
    for frame in pd.read_csv(path, usecols=names, chunksize=100000):
        stamps.append(frame[names[0]].to_numpy(np.int64))
        arrays.append(frame[names[1:]].to_numpy(float))
    ns, values = np.concatenate(stamps), np.concatenate(arrays)
    order = np.argsort(ns, kind="stable")
    ns, values = ns[order], values[order]
    bin_ns = int(1e9/rate)
    bins = ns//bin_ns
    first, last = int(np.ceil(ns[0]/1e9)), int(ns[-1]//1000000000)
    n = (last-first)*rate
    index = bins-first*rate
    good = (index >= 0) & (index < n)
    count = np.bincount(index[good], minlength=n)
    missing = count == 0
    mean = np.column_stack([np.bincount(index[good], weights=values[good, j],
                                       minlength=n)/np.maximum(count, 1) for j in range(6)])
    # Only fill gaps shorter than 30 ms. Fail visibly on larger raw-data gaps.
    missing_i = np.flatnonzero(missing)
    longest = 0
    if len(missing_i):
        runs = np.split(missing_i, np.flatnonzero(np.diff(missing_i) > 1)+1)
        longest = max(map(len, runs))
        if longest > 2:
            raise ValueError(f"IMU gap exceeds 20 ms: {longest/rate:.3f} s")
        for j in range(6):
            mean[missing, j] = np.interp(missing_i, np.flatnonzero(~missing), mean[~missing, j])
    times = first+np.arange(n)/rate
    stats = {"raw_samples": len(ns), "rate_hz": rate,
             "raw_max_gap_s": float(np.max(np.diff(ns))/1e9),
             "filled_empty_bins": int(missing.sum()), "longest_filled_gap_s": longest/rate,
             "seconds": last-first}
    return times, mean.astype(np.float32), np.arange(first, last+1, dtype=float), stats


def prepare(root, sequence, cfg, force=False):
    source = root/"data/raw/UrbanNav"/sequence
    dest = root/"data/processed"/sequence
    dest.mkdir(parents=True, exist_ok=True)
    files = [dest/"inputs.npz", dest/"reference.npz", dest/"manifest.json"]
    settings = preparation_settings(cfg)
    if all(p.exists() for p in files) and not force:
        old = json.loads(files[2].read_text())
        if (old.get("preparation_settings") == settings and old.get("rtklib_sha256") ==
                digest(root/"external/RTKLIB_bin/rnx2rtkp.exe")):
            if all((root/"data/raw/UrbanNav"/sequence/v["relative_path"]).stat().st_size == v["bytes"]
                   and (root/"data/raw/UrbanNav"/sequence/v["relative_path"]).stat().st_mtime_ns == v.get("mtime_ns")
                   for v in old["sources"].values()):
                return
    paths = {k: source/v for k, v in SEQUENCES[sequence].items()}
    if not all(p.is_file() for p in paths.values()):
        raise FileNotFoundError("The UrbanNav files listed in datasets/README.md are required.")
    run_frontend(root, paths, dest, cfg)
    dgnss, spp = (read_positions(dest/f"gnss_{s}.pos") for s in ["dgnss", "spp"])
    imu_t, imu, epoch_t, stats = read_imu(paths["imu"], cfg["imu_rate_hz"])
    available = sorted(set(dgnss)|set(spp))
    origin = (dgnss.get(available[0]) or spp[available[0]])[0]
    frame = ecef_frame(origin)
    p = np.full((len(epoch_t), 3), np.nan)
    cov = np.full((len(epoch_t), 3, 3), np.nan)
    mode = np.zeros(len(epoch_t), dtype=np.uint8)
    quality = np.zeros_like(mode)
    satellites = np.zeros_like(mode)
    for i, t in enumerate(epoch_t.astype(np.int64)):
        if t not in dgnss and t not in spp:
            continue
        differential = t in dgnss
        point, c, q, ns = dgnss[t] if differential else spp[t]
        c = frame@c@frame.T
        eigenvalues, eigenvectors = np.linalg.eigh(c)
        floor = cfg["dgnss_sigma_floor_m"] if differential else cfg["spp_sigma_floor_m"]
        c = (eigenvectors*np.maximum(eigenvalues, floor**2))@eigenvectors.T
        p[i], cov[i] = frame@(point-origin), c
        mode[i], quality[i], satellites[i] = 1 if differential else 2, q, ns
    np.savez_compressed(files[0], imu_t=imu_t, imu=imu, epoch_t=epoch_t,
                        imu_rate_hz=np.array(cfg["imu_rate_hz"]), gnss_p=p,
                        gnss_cov=cov, gnss_mode=mode, gnss_quality=quality,
                        satellites=satellites, origin_ecef=origin, ecef_to_enu=frame)
    ref = np.loadtxt(paths["reference"], skiprows=2)
    lat = ref[:, 3]+ref[:, 4]/60+ref[:, 5]/3600
    lon = ref[:, 6]+ref[:, 7]/60+ref[:, 8]/3600
    ref_p = (lla_ecef(lat, lon, ref[:, 9])-origin)@frame.T
    np.savez_compressed(files[1], t=ref[:, 0], p=ref_p, quality=ref[:, 19].astype(np.uint8))
    manifest = {"sequence": sequence, "imu": stats, "preparation_settings": settings,
                "rtklib_sha256": digest(root/"external/RTKLIB_bin/rnx2rtkp.exe"),
                "dgnss_epochs": int((mode == 1).sum()),
                "spp_fallback_epochs": int((mode == 2).sum()),
                "missing_gnss_epochs": int((mode == 0).sum()),
                "reference_epochs": len(ref),
                "reference_quality_counts": {str(int(q)): int((ref[:, 19] == q).sum())
                                             for q in np.unique(ref[:, 19])},
                "origin_ecef_m": origin.tolist(), "config": cfg,
                "sources": {k: {"relative_path": v.relative_to(source).as_posix(), "bytes": v.stat().st_size,
                                "mtime_ns": v.stat().st_mtime_ns,
                                "sha256": digest(v)} for k, v in paths.items()}}
    for name in ["extrinsic.yaml", "xsens_imu_param.yaml"]:
        v = source/"calibration"/name
        manifest["sources"][name] = {"relative_path": v.relative_to(source).as_posix(),
                                     "bytes": v.stat().st_size, "mtime_ns": v.stat().st_mtime_ns,
                                     "sha256": digest(v)}
    files[2].write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Prepared {sequence}: {len(epoch_t)} epochs, {stats['raw_samples']} IMU samples.", flush=True)
