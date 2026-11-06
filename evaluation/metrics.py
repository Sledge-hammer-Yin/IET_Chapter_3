"""Evaluate the same UTC epochs without fitted trajectory alignment."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np


def matched_reference(t, reference):
    index = np.searchsorted(reference["t"], t)
    index = np.minimum(index, len(reference["t"])-1)
    prev = np.maximum(index-1, 0)
    index = np.where(abs(reference["t"][prev]-t) < abs(reference["t"][index]-t), prev, index)
    valid = abs(reference["t"][index]-t) < .002
    return reference["p"][index], valid


def evaluate(result, reference, meta, cfg):
    ref, matched = matched_reference(result["t"], reference)
    scored = (result["t"] >= result["t"][0]+cfg["settling_seconds"]) & matched
    finite = np.isfinite(result["p"]).all(axis=1)
    mask = scored & finite
    if not mask.any():
        raise ValueError("No common evaluation epochs.")
    err = result["p"]-ref
    e3, eh, ev = np.linalg.norm(err[mask], axis=1), np.linalg.norm(err[mask, :2], axis=1), err[mask, 2]
    rpe = []
    for i in np.flatnonzero(mask):
        j = i+10
        if j < len(mask) and mask[j] and abs(result["t"][j]-result["t"][i]-10) < .002:
            rpe.append(np.linalg.norm(err[j]-err[i]))
    available = result["gnss_available"].astype(bool)
    accepted = result["gnss_accepted"].astype(bool)
    return {"sequence": meta["sequence"], "method": meta["method"],
            "epochs": int(mask.sum()), "output_coverage_pct": float(mask.sum()/scored.sum()*100),
            "evaluated_fraction_of_input_pct": float(mask.sum()/meta["input_epochs"]*100),
            "rmse_3d_m": float(np.sqrt(np.mean(e3**2))),
            "rmse_horizontal_m": float(np.sqrt(np.mean(eh**2))),
            "rmse_vertical_m": float(np.sqrt(np.mean(ev**2))),
            "p95_3d_m": float(np.percentile(e3, 95)), "max_3d_m": float(e3.max()),
            "rpe_10s_rmse_m": float(np.sqrt(np.mean(np.array(rpe)**2))),
            "gnss_available_epochs": int(available[scored].sum()),
            "gnss_rejected_epochs": int((available & ~accepted & scored).sum()),
            "mean_epoch_ms": float(meta["estimator_seconds"]/(len(result["t"])-1)*1000),
            "p95_epoch_ms": float(np.percentile(result["epoch_ms"][1:], 95)),
            "sampled_peak_rss_mib": meta["sampled_peak_rss_mib"]}


def summarize(project, cfg, sequences):
    rows = []
    for sequence in sequences:
        reference = dict(np.load(project.parent/"data/processed"/sequence/"reference.npz"))
        current_input = hashlib.sha256((project.parent/"data/processed"/sequence/"inputs.npz").read_bytes()).hexdigest()
        common_time, common_input, common_source = None, None, None
        for method in ["B1_ESKF", "B2_ESKF_NIS", "B3_GNSS_IMU_FGO"]:
            folder = project/"results"/sequence
            result = dict(np.load(folder/f"{method}.npz"))
            meta = json.loads((folder/f"{method}.json").read_text())
            if meta["config"] != cfg or meta["smoke_only"] or meta["input_sha256"] != current_input:
                raise ValueError("Results/configuration mismatch. Rerun all methods before summarizing.")
            if common_time is None:
                common_time = result["t"]
                common_input = meta["input_sha256"]
                common_source = meta["estimator_source_sha256"]
            elif (not np.array_equal(result["t"], common_time) or meta["input_sha256"] != common_input
                  or meta["estimator_source_sha256"] != common_source):
                raise ValueError("Methods do not share the same timestamps, input or source version.")
            rows.append(evaluate(result, reference, meta, cfg))
    folder = project/"results" if len(sequences) > 1 else project/"results"/sequences[0]
    path = folder/"metrics.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: round(v, 4) if isinstance(v, float) else v for k, v in row.items()})
    (folder/"metrics.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return rows
