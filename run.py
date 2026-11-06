"""Small local UrbanNav benchmark. Run with the isolated b123 Python."""
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

for name in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"]:
    os.environ[name] = "1"
if os.name == "nt":
    dll_path = Path(sys.prefix)/"Library/bin"
    os.environ["PATH"] = str(dll_path)+os.pathsep+os.environ.get("PATH", "")
    if dll_path.is_dir():
        _dll_handle = os.add_dll_directory(str(dll_path))

import argparse
import json
import platform
import subprocess
import time
import importlib.metadata
import hashlib
import numpy as np
import psutil
from algorithms.common import initial_state, interval_samples

PROJECT = Path(__file__).resolve().parent
ROOT = PROJECT.parent
METHODS = ["B1_ESKF", "B2_ESKF_NIS", "B3_GNSS_IMU_FGO"]
SEQUENCES = ["Deep-Urban-1", "Medium-Urban-1"]


def run_one(sequence, method, cfg, max_seconds=0):
    manifest_file = ROOT/"data/processed"/sequence/"manifest.json"
    if not manifest_file.is_file():
        raise FileNotFoundError("Run 'python run.py prepare' first.")
    manifest = json.loads(manifest_file.read_text())
    prepared = manifest.get("preparation_settings", {})
    if not prepared or any(cfg[k] != v for k, v in prepared.items()):
        raise ValueError("Input settings changed. Run 'python run.py prepare' first.")
    data = dict(np.load(ROOT/"data/processed"/sequence/"inputs.npz"))
    start, state = initial_state(data, cfg)
    initial = state.copy()
    if method == METHODS[0]:
        from algorithms.B1_ESKF import ESKF
        estimator = ESKF(state, cfg)
    elif method == METHODS[1]:
        from algorithms.B2_ESKF_NIS import GatedESKF
        estimator = GatedESKF(state, cfg)
    else:
        from algorithms.B3_GNSS_IMU_FGO import FixedLagGNSSIMU
        estimator = FixedLagGNSSIMU(state, cfg, data["epoch_t"][start])
    end = len(data["epoch_t"])
    if max_seconds:
        end = min(end, start+max_seconds+1)
    times = data["epoch_t"][start:end]
    n = len(times)
    positions, velocities = np.empty((n, 3)), np.empty((n, 3))
    biases = np.empty((n, 6))
    nis, accepted, elapsed = np.full(n, np.nan), np.zeros(n, np.uint8), np.zeros(n)
    updates, cost = np.zeros(n, np.uint8), np.full(n, np.nan)
    available = np.isfinite(data["gnss_p"][start:end]).all(axis=1).astype(np.uint8)
    process = psutil.Process()
    peak = process.memory_info().rss
    total = 0.
    lever = np.array(cfg["reference_lever_body_m"])
    positions[0], velocities[0] = state.p+state.R@lever, state.v
    biases[0] = np.r_[state.bg, state.ba]
    for j in range(1, n):
        i = start+j
        tick = time.perf_counter()
        samples, dt = interval_samples(data, times[j-1], times[j])
        if len(samples) != cfg["imu_rate_hz"]:
            raise ValueError(f"Incomplete IMU interval at {times[j]}: {len(samples)} samples")
        position = data["gnss_p"][i] if available[j] else None
        covariance = data["gnss_cov"][i] if available[j] else None
        if method == METHODS[2]:
            state = estimator.step(samples, dt, times[j], position, covariance)
            updates[j], cost[j] = estimator.updates, estimator.cost
            accepted[j] = available[j]
        else:
            estimator.propagate(samples, dt)
            if available[j]:
                accepted[j] = estimator.update(position, covariance)
                nis[j] = estimator.nis
            state = estimator.s
        elapsed[j] = (time.perf_counter()-tick)*1000
        total += elapsed[j]/1000
        positions[j], velocities[j] = state.p+state.R@lever, state.v
        biases[j] = np.r_[state.bg, state.ba]
        if not np.isfinite(np.r_[positions[j], velocities[j], biases[j]]).all():
            raise FloatingPointError("Non-finite navigation state")
        peak = max(peak, process.memory_info().rss)
        if j % 300 == 0:
            print(f"{sequence} {method}: {j}/{n-1} s", flush=True)
    folder = PROJECT/("results/smoke" if max_seconds else "results")/sequence
    folder.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(folder/f"{method}.npz", t=times, p=positions, v=velocities,
                        bias=biases, nis=nis.astype(np.float32),
                        gnss_available=available, gnss_accepted=accepted,
                        optimizer_updates=updates, optimizer_cost=cost,
                        epoch_ms=elapsed.astype(np.float32))
    meta = {"sequence": sequence, "method": method, "epochs": n,
            "start_utc_unix": float(times[0]), "end_utc_unix": float(times[-1]),
            "input_epochs": len(data["epoch_t"]),
            "initialization_delay_s": float(times[0]-data["epoch_t"][0]),
            "estimator_seconds": total, "sampled_peak_rss_mib": peak/2**20,
            "initial_state": {k: getattr(initial, k).tolist()
                              for k in ["p", "v", "R", "bg", "ba"]},
            "config": cfg, "python": sys.version.split()[0], "platform": platform.platform(),
            "versions": {p: importlib.metadata.version(p) for p in ["numpy", "scipy", "matplotlib"]},
            "truth_used_by_estimator": False, "smoke_only": bool(max_seconds),
            "input_sha256": hashlib.sha256((manifest_file.parent/"inputs.npz").read_bytes()).hexdigest(),
            "output_policy": "Current causal state at 1 Hz; no revised past states are scored."}
    h = hashlib.sha256()
    sources = sorted((PROJECT/"algorithms").rglob("*.py"))+[PROJECT/"run.py"]
    for path in sources:
        h.update(path.relative_to(PROJECT).as_posix().encode())
        h.update(path.read_bytes())
    meta["estimator_source_sha256"] = h.hexdigest()
    if method == METHODS[2]:
        meta["gtsam"] = "4.2.0 (conda-forge Windows, incremental fixed-lag smoother)"
        meta["solver"] = "iSAM2 QR; incremental approximate MAP with marginalization"
    (folder/f"{method}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Finished {sequence} {method}: {total:.2f} s, sampled RSS {peak/2**20:.1f} MiB.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "run", "summarize", "plot", "all", "test", "install-rtklib"])
    parser.add_argument("--sequence", choices=["all"]+SEQUENCES, default="all")
    parser.add_argument("--method", choices=["all"]+METHODS, default="all")
    parser.add_argument("--config", type=Path, default=PROJECT/"configs/benchmark.json")
    parser.add_argument("--max-seconds", type=int, default=0, help="Smoke run; saved separately.")
    parser.add_argument("--force", action="store_true", help="Rebuild compact inputs, not raw data.")
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text())
    sequences = SEQUENCES if args.sequence == "all" else [args.sequence]
    methods = METHODS if args.method == "all" else [args.method]
    rows = None
    if args.action == "install-rtklib":
        from datasets.install_rtklib import install
        install(PROJECT)
    if args.action == "test":
        import unittest
        suite = unittest.defaultTestLoader.discover(str(PROJECT/"tests"))
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        report = {"utc": datetime.now(timezone.utc).isoformat(), "tests": result.testsRun,
                  "failures": len(result.failures), "errors": len(result.errors),
                  "passed": result.wasSuccessful()}
        (PROJECT/"results").mkdir(exist_ok=True)
        (PROJECT/"results/test_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        if not result.wasSuccessful():
            raise SystemExit(1)
    if args.action in ["prepare", "all"]:
        from datasets.prepare import prepare
        for sequence in sequences:
            prepare(ROOT, sequence, cfg, args.force)
    if args.action in ["run", "all"]:
        if len(sequences)*len(methods) == 1:
            run_one(sequences[0], methods[0], cfg, args.max_seconds)
        else:
            for sequence in sequences:
                for method in methods:
                    subprocess.run([sys.executable, str(PROJECT/"run.py"), "run", "--sequence", sequence,
                                    "--method", method, "--config", str(args.config),
                                    "--max-seconds", str(args.max_seconds)], check=True)
    if args.action in ["summarize", "all"] and not args.max_seconds:
        from evaluation.metrics import summarize
        rows = summarize(PROJECT, cfg, sequences)
        for row in rows:
            print(f"{row['sequence']} {row['method']}: 3D RMSE {row['rmse_3d_m']:.2f} m")
    if args.action in ["plot", "all"] and not args.max_seconds:
        from evaluation.plot import plot_all
        plot_all(PROJECT, cfg, sequences)
    if rows is not None:
        from evaluation.report import write_reports
        write_reports(PROJECT, cfg, sequences, rows)


if __name__ == "__main__":
    main()
