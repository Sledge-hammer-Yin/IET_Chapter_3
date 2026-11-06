"""Build concise English reports from actual saved outputs, not preset scores."""
import hashlib
import json
import platform
import shutil
import sys
from datetime import datetime, timezone
import numpy as np
import psutil


def utc(t):
    return datetime.fromtimestamp(float(t), timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def write_reports(project, cfg, sequences, rows):
    full = ["Deep-Urban-1", "Medium-Urban-1"]
    if sorted(sequences) != sorted(full):
        return  # The manuscript report describes the complete two-sequence comparison.
    details = {}
    manifests = project/"datasets/manifests"
    manifests.mkdir(exist_ok=True)
    for sequence in full:
        folder = project.parent/"data/processed"/sequence
        inputs = dict(np.load(folder/"inputs.npz"))
        manifest = json.loads((folder/"manifest.json").read_text())
        (manifests/f"{sequence}.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        meta = json.loads((project/"results"/sequence/"B1_ESKF.json").read_text())
        absent = np.flatnonzero(~np.isfinite(inputs["gnss_p"]).all(axis=1))
        runs = np.split(absent, np.flatnonzero(np.diff(absent) > 1)+1)
        details[sequence] = {"input_epochs": len(inputs["epoch_t"]),
            "dgnss_epochs": manifest["dgnss_epochs"], "spp_fallback_epochs": manifest["spp_fallback_epochs"],
            "missing_gnss_epochs": manifest["missing_gnss_epochs"],
            "longest_missing_gnss_s": max(map(len, runs)),
            "initialization_delay_s": meta["initialization_delay_s"],
            "estimator_start_utc": utc(meta["start_utc_unix"]),
            "scoring_start_utc": utc(meta["start_utc_unix"]+cfg["settling_seconds"]),
            "end_utc": utc(meta["end_utc_unix"]),
            "reference_quality_counts": manifest["reference_quality_counts"]}
    summary = {"generated_utc": datetime.now(timezone.utc).isoformat(),
               "platform": platform.platform(), "python": sys.version.split()[0],
               "physical_cores": psutil.cpu_count(logical=False),
               "logical_cores": psutil.cpu_count(), "ram_gib": psutil.virtual_memory().total/2**30,
               "free_disk_gib": shutil.disk_usage(project).free/2**30, "sequences": details}
    (project/"results/run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lookup = {(r["sequence"], r["method"]): r for r in rows}
    table = "| Sequence | B1 RMSE (m) | B2 RMSE (m) | B3 RMSE (m) |\n|---|---:|---:|---:|\n"
    for s in full:
        table += "| "+s+" | "+" | ".join(f"{lookup[s, m]['rmse_3d_m']:.2f}" for m in
                                ["B1_ESKF", "B2_ESKF_NIS", "B3_GNSS_IMU_FGO"])+" |\n"
    deep_change = 100*(1-lookup[full[0], "B2_ESKF_NIS"]["rmse_3d_m"]/
                      lookup[full[0], "B1_ESKF"]["rmse_3d_m"])
    medium_change = 100*(lookup[full[1], "B2_ESKF_NIS"]["rmse_3d_m"]/
                        lookup[full[1], "B1_ESKF"]["rmse_3d_m"]-1)
    deep_effect = f"{'reduces' if deep_change >= 0 else 'increases'} the 3D RMSE by {abs(deep_change):.1f}%"
    medium_effect = f"{'increases' if medium_change >= 0 else 'reduces'} it by {abs(medium_change):.1f}%"
    largest_error = max(r["max_3d_m"] for r in rows)
    paragraph1 = ("The three estimators were evaluated on the UrbanNav-HK-Deep-Urban-1 and "
        "UrbanNav-HK-Medium-Urban-1 ground-vehicle sequences [23]. B1 is a GNSS/IMU ESKF, "
        "B2 adds NIS-based observation rejection, and B3 uses IMU preintegration in a 5 s "
        "GNSS/IMU factor graph. The estimators use the same observations, initial state, "
        "noise settings and evaluation epochs. Position errors are measured against the "
        "provided reference trajectories without fitted trajectory alignment.")
    paragraph2 = (f"Figures 3.9 and 3.10 show that the relative performance depends on the "
        f"sequence. NIS gating {deep_effect} on Deep-Urban-1, "
        f"and {medium_effect} on Medium-Urban-1. The corresponding B3 RMSE values are "
        f"{lookup[full[0], 'B3_GNSS_IMU_FGO']['rmse_3d_m']:.2f} m and "
        f"{lookup[full[1], 'B3_GNSS_IMU_FGO']['rmse_3d_m']:.2f} m. Residual errors remain. These "
        "results illustrate the effects of observation rejection and window-based "
        "estimation, rather than establishing a general ranking or UAV flight performance.")
    chapter = f"""# Chapter 3: measured results and manuscript insertion

## Can these results be included?

Yes, as a small reproducible implementation example and an illustration of limitations. They support the GNSS/IMU methods in 1.4.1--1.4.5. They are not a GLIO reproduction, a UAV flight test or evidence of high-accuracy positioning. The maximum error reaches {largest_error:.1f} m under this configuration. The varying reference quality also limits fine accuracy claims. Do not describe output continuity as accurate navigation or claim that NIS/FGO always improves ESKF.

## Actual common-epoch results

{table}
B1: ESKF. B2: the same ESKF with NIS gating. B3: fixed-lag GNSS/IMU factor graph with preintegration. Full horizontal/vertical RMSE, 3D P95/maximum, 10 s relative translation RMSE, timing and memory are in `results/metrics.csv`. Deep uses {lookup[full[0], 'B1_ESKF']['epochs']} scored epochs; Medium uses {lookup[full[1], 'B1_ESKF']['epochs']}. All methods have finite outputs at 100% of those epochs. This excludes initialization and {cfg['settling_seconds']} s of settling, retaining {lookup[full[0], 'B1_ESKF']['evaluated_fraction_of_input_pct']:.2f}% and {lookup[full[1], 'B1_ESKF']['evaluated_fraction_of_input_pct']:.2f}% of the complete input timelines, respectively.

B2 rejects {lookup[full[0], 'B2_ESKF_NIS']['gnss_rejected_epochs']} of {lookup[full[0], 'B2_ESKF_NIS']['gnss_available_epochs']} available fixes in the Deep scoring interval and {lookup[full[1], 'B2_ESKF_NIS']['gnss_rejected_epochs']} of {lookup[full[1], 'B2_ESKF_NIS']['gnss_available_epochs']} in Medium. Rejection can remove an outlier, but a drifting prediction can also reject a useful returning fix. The present results do not isolate every error's cause. The frontend has intervals without a position fix lasting up to {details[full[0]]['longest_missing_gnss_s']} s and {details[full[1]]['longest_missing_gnss_s']} s over the complete input timelines.

## Minimal placement

Add one experimental block at the end of 1.4.5, after its final discussion of window length and computational cost, immediately before the 1.4.6 GLIO heading. This keeps the B1--B3 comparison with the general estimation methods and keeps the GLIO case study separate. Add no new numbered subsection. Number the new error plots Figures 3.9 and 3.10, and renumber the existing GLIO figure as Figure 3.11 in its text mention, insertion placeholder and caption.

Use only two single-panel error plots: `results/figures/Deep-Urban-1_error.png` and `results/figures/Medium-Urban-1_error.png`. Both use a logarithmic vertical axis. The trajectory plots are supplementary and can stay in the repository. Add the small two-row RMSE table above only if space permits; assign its number after the existing chapter tables. Do not add the runtime/memory table to the main chapter because Python and compiled-C++ workloads differ.

Paste these two short paragraphs:

{paragraph1}

{paragraph2}

Suggested captions:

Figure 3.9  Three-dimensional position errors on UrbanNav-HK-Deep-Urban-1. B1: ESKF; B2: ESKF with NIS gating; B3: GNSS/IMU fixed-lag factor graph. The vertical axis uses a logarithmic scale.

Figure 3.10  Three-dimensional position errors on UrbanNav-HK-Medium-Urban-1. The methods and evaluation settings are the same as in Figure 3.9. The vertical axis uses a logarithmic scale.

Copy paragraph styles from the existing 1.4.1 body, and copy caption style and spacing from the existing figure captions. Insert images inline at about 11.5 cm width, preserving aspect ratio. PNG files are 300 dpi; PDF files embed Times New Roman for vector export. Do not turn these paragraphs into new heading levels. This Markdown supplies content and placement; the original Word file has not been changed.

## References and scope

In the inspected Word file, [23] is UrbanNav, [2] and [3] cover estimation/filtering, [7] covers GNSS/INS FGO versus EKF, and [16] covers improved inertial preintegration. Reuse these references where appropriate. The new data paragraph introduces the already-listed [23] earlier, in 1.4.5, after the existing first citation of [22] in 1.4.3 and before [24]. The numbered reference order therefore stays unchanged, and no new paper is needed. These are newly measured outputs, not numbers copied from [7].

GTSAM 4.2 and RTKLIB 2.4.3 b34 are acknowledged with official links and versions in the repository. Native KF-GINS was not executed, so do not add its paper while describing these results as a KF-GINS reproduction. If iSAM2 itself is explained in new theoretical text, cite its original method paper rather than presenting that method as new. If a revised manuscript has already renumbered the references, match the UrbanNav citation by title before pasting.

Before publication, check the existing IMU-preintegration equations against the corrected source text: the velocity summand must use the intermediate rotation indexed by the IMU sample, the second-order position term must include the bias-corrected specific force, and the gravity term must use the squared full keyframe interval. The executable implementation does not use those transcription errors. This note does not change the original document.
"""
    (project/"CHAPTER3_RESULTS.md").write_text(chapter, encoding="utf-8")
    timing = "| Sequence | Method | 3D RMSE (m) | P95 (m) | Mean ms/epoch | Sampled RSS (MiB) |\n|---|---|---:|---:|---:|---:|\n"
    for r in rows:
        timing += (f"| {r['sequence']} | {r['method'].split('_')[0]} | {r['rmse_3d_m']:.2f} | "
                   f"{r['p95_3d_m']:.2f} | {r['mean_epoch_ms']:.2f} | {r['sampled_peak_rss_mib']:.1f} |\n")
    readme = f"""# Actual benchmark outputs

{timing}
One epoch is a 1 s input interval containing 100 IMU samples. Timing excludes input conversion and plotting. B1/B2 have Python propagation loops, while B3 calls compiled GTSAM; these timings do not establish an intrinsic algorithm-speed ranking. RSS includes the Python process and its libraries, sampled at 1 Hz.

Each sequence contains one compressed NPZ and one small metadata JSON per estimator. NPZ fields are UTC time, estimated reference-point position, velocity, biases, NIS where applicable, observation-availability/acceptance flags, epoch time, and B3 update/cost diagnostics. B3 cost values are local-window diagnostics, not an accuracy metric or a quantity directly comparable to another window.

`metrics.csv` and `metrics.json` use a common matched interval for all methods, with no trajectory alignment or method-specific trimming. `run_summary.json` records startup times, fix availability and hardware. Dataset source hashes are in `../datasets/manifests`. `source_manifest.json` records implementation/configuration hashes. `test_report.json` records the numerical checks.

The `figures` folder contains four independent figures, each as a 300 dpi PNG and a vector PDF. The two error plots use logarithmic vertical axes. No smoothing, clipped error peaks or selected best segments are used. Figures cover only the common scoring interval; startup exclusions are recorded explicitly. Recommended chapter use is described in `../CHAPTER3_RESULTS.md`.
"""
    (project/"results/README.md").write_text(readme, encoding="utf-8")
    validation = f"""# Validation and limits

The seven numerical checks cover stationary gravity compensation and covariance positivity; analytic constant-turn motion; B1/B2 equivalence with gating disabled and outlier rejection; causal initialization; the antenna-factor Jacobian against central differences; fixed-lag marginalization; and motion through a synthetic GNSS outage and reacquisition. Test status is saved in `results/test_report.json`. Passing these checks supports implementation correctness; it does not prove accuracy or consistency for every motion/noise condition.

All six complete estimator runs finished and produced finite current-state outputs. No reference data were used by the estimators. Both sequences use identical settings, with the separate reference files opened only during evaluation. Source manifests record the exact input bytes. The explicit RTKLIB mask was checked against the earlier frontend output and produced identical GNSS positions; no GPS-only claim is made. The final B3 uses the upstream incremental fixed-lag QR solver, not a custom replacement for marginalization.

| Sequence | Input epochs | DGNSS | SPP fallback | No GNSS fix | Longest no-fix interval (s) | Startup (s) |
|---|---:|---:|---:|---:|---:|---:|
"""
    for s, d in details.items():
        validation += (f"| {s} | {d['input_epochs']} | {d['dgnss_epochs']} | {d['spp_fallback_epochs']} | "
                       f"{d['missing_gnss_epochs']} | {d['longest_missing_gnss_s']} | {d['initialization_delay_s']:.0f} |\n")
    validation += "\n| Sequence | Scoring starts (UTC) | Ends (UTC) | Reference quality-code counts |\n|---|---|---|---|\n"
    for s, d in details.items():
        validation += f"| {s} | {d['scoring_start_utc']} | {d['end_utc']} | {d['reference_quality_counts']} |\n"
    validation += f"""
The machine reports {summary['physical_cores']} physical / {summary['logical_cores']} logical CPU cores and {summary['ram_gib']:.1f} GiB RAM. The isolated environment uses Python {summary['python']}; exact packages are pinned in `environment-win-64.lock.txt`. GPU acceleration, ROS and Ubuntu are not needed. Existing user environments and raw files are unchanged.

Important limits: this is local flat-ENU navigation with fixed gravity, without Earth/transport-rate compensation, scale-factor estimation, Doppler constraints or dedicated outage recovery. Initial yaw uses a vehicle-forward assumption. Fixed measurement-noise floors and the calibration noise interpretation are declared modeling choices, not optimized reference-error fits. Long intervals without a frontend fix and unreliable urban observations remain difficult; the plots retain the resulting large peaks. Two sequences cannot establish statistical generality, and varying SPAN reference quality prevents a blanket centimetre-accuracy claim. The comparison is internal to these implementations, not a reproduction of the published KF-GINS/GLIO results or a UAV flight validation.

Plot text, including logarithmic-axis tick labels, is configured as Times New Roman. Figures use single axes, colorblind-friendly colors, 10 pt text (9 pt ticks/legends), 1.1 pt curves and tight margins. PNG/PDF files are generated from the same figure objects. Raw IMU, intermediate covariance matrices and point clouds are not duplicated in the results. Re-running overwrites each estimator's small outputs instead of creating timestamped copies.
"""
    (project/"VALIDATION.md").write_text(validation, encoding="utf-8")
    source_manifest = {}
    for path in sorted(project.rglob("*")):
        if not path.is_file() or any(x in path.parts for x in [".git", "__pycache__", "results"]):
            continue
        if path.suffix not in [".py", ".json", ".yml", ".ps1", ".txt"]:
            continue
        source_manifest[path.relative_to(project).as_posix()] = {
            "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    (project/"results/source_manifest.json").write_text(json.dumps(source_manifest, indent=2), encoding="utf-8")
    print("Updated CHAPTER3_RESULTS.md, VALIDATION.md and the result/provenance reports.")
