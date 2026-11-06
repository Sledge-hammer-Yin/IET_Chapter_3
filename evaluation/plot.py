"""Four compact single-panel figures, with verified Times New Roman text."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from evaluation.metrics import matched_reference

COLORS = ["#0072B2", "#D55E00", "#009E73"]
METHODS = ["B1_ESKF", "B2_ESKF_NIS", "B3_GNSS_IMU_FGO"]


def plot_all(project, cfg, sequences):
    font = Path("C:/Windows/Fonts/times.ttf")
    if not font.exists():
        raise FileNotFoundError("Install Times New Roman before making publication figures.")
    font_manager.fontManager.addfont(str(font))
    plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10,
                         "axes.labelsize": 10, "xtick.labelsize": 9, "ytick.labelsize": 9,
                         "legend.fontsize": 9, "lines.linewidth": 1.1, "axes.linewidth": .7,
                         "xtick.major.width": .7, "ytick.major.width": .7,
                         "pdf.fonttype": 42, "ps.fonttype": 42,
                         "mathtext.fontset": "custom", "mathtext.rm": "Times New Roman",
                         "mathtext.it": "Times New Roman:italic", "mathtext.bf": "Times New Roman:bold",
                         "mathtext.sf": "Times New Roman", "mathtext.tt": "Times New Roman",
                         "mathtext.cal": "Times New Roman", "mathtext.fallback": None,
                         "mathtext.default": "regular",
                         "savefig.dpi": 300, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.formatter.useoffset": False})
    assert "times" in font_manager.findfont("Times New Roman").lower()
    folder = project/"results/figures"
    folder.mkdir(parents=True, exist_ok=True)
    for sequence in sequences:
        reference = dict(np.load(project.parent/"data/processed"/sequence/"reference.npz"))
        outputs = [dict(np.load(project/"results"/sequence/f"{m}.npz")) for m in METHODS]
        t = outputs[0]["t"]
        ref, match = matched_reference(t, reference)
        mask = match & (t >= t[0]+cfg["settling_seconds"])
        if not all(np.array_equal(o["t"], t) for o in outputs):
            raise ValueError("The three output schedules must be identical.")
        for kind in ["trajectory", "error"]:
            fig, ax = plt.subplots(figsize=(3.8, 4.) if kind == "trajectory" else (4.6, 3.15),
                                   layout="constrained")
            if kind == "trajectory":
                ax.plot(ref[mask, 0], ref[mask, 1], color="#222222", linestyle="--",
                        linewidth=1.2, label="Reference", zorder=4)
                for j, output in enumerate(outputs):
                    ax.plot(output["p"][mask, 0], output["p"][mask, 1],
                            color=COLORS[j], label=f"B{j+1}", alpha=.9)
                ax.set(xlabel="East (m)", ylabel="North (m)")
                ax.set_aspect("equal", adjustable="box")
                ax.legend(loc="lower center", bbox_to_anchor=(.5, 1.01), ncol=4,
                          frameon=False, handlelength=1.3, columnspacing=.8, handletextpad=.4)
            else:
                errors = []
                for j, output in enumerate(outputs):
                    err = np.linalg.norm(output["p"]-ref, axis=1)
                    errors.append(err[mask])
                    ax.plot((t[mask]-t[mask][0])/60, err[mask], color=COLORS[j], label=f"B{j+1}")
                if max(np.max(e) for e in errors) > 100:
                    ax.set_yscale("log")
                ax.set(xlabel="Evaluation time (min)", ylabel="3D position error (m)")
                ax.legend(loc="best", frameon=False, handlelength=1.6, ncol=3)
                ax.grid(axis="y", which="major", linewidth=.4, alpha=.25)
            for ext in ["png", "pdf"]:
                fig.savefig(folder/f"{sequence}_{kind}.{ext}", bbox_inches="tight", pad_inches=.04)
            plt.close(fig)
    print(f"Saved {len(sequences)*2} single-panel figures as PNG and PDF.")
