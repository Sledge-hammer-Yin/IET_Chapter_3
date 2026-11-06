# Chapter 3: measured results and manuscript insertion

## Can these results be included?

Yes, as a small reproducible implementation example and an illustration of limitations. They support the GNSS/IMU methods in 1.4.1--1.4.5. They are not a GLIO reproduction, a UAV flight test or evidence of high-accuracy positioning. The maximum error reaches 722.6 m under this configuration. The varying reference quality also limits fine accuracy claims. Do not describe output continuity as accurate navigation or claim that NIS/FGO always improves ESKF.

## Actual common-epoch results

| Sequence | B1 RMSE (m) | B2 RMSE (m) | B3 RMSE (m) |
|---|---:|---:|---:|
| Deep-Urban-1 | 101.85 | 91.11 | 98.53 |
| Medium-Urban-1 | 35.60 | 62.48 | 34.52 |

B1: ESKF. B2: the same ESKF with NIS gating. B3: fixed-lag GNSS/IMU factor graph with preintegration. Full horizontal/vertical RMSE, 3D P95/maximum, 10 s relative translation RMSE, timing and memory are in `results/metrics.csv`. Deep uses 1444 scored epochs; Medium uses 655. All methods have finite outputs at 100% of those epochs. This excludes initialization and 30 s of settling, retaining 93.95% and 83.33% of the complete input timelines, respectively.

B2 rejects 125 of 871 available fixes in the Deep scoring interval and 110 of 385 in Medium. Rejection can remove an outlier, but a drifting prediction can also reject a useful returning fix. The present results do not isolate every error's cause. The frontend has intervals without a position fix lasting up to 74 s and 59 s over the complete input timelines.

## Minimal placement

Add one experimental block at the end of 1.4.5, after its final discussion of window length and computational cost, immediately before the 1.4.6 GLIO heading. This keeps the B1--B3 comparison with the general estimation methods and keeps the GLIO case study separate. Add no new numbered subsection. Number the new error plots Figures 3.9 and 3.10, and renumber the existing GLIO figure as Figure 3.11 in its text mention, insertion placeholder and caption.

Use only two single-panel error plots: `results/figures/Deep-Urban-1_error.png` and `results/figures/Medium-Urban-1_error.png`. Both use a logarithmic vertical axis. The trajectory plots are supplementary and can stay in the repository. Add the small two-row RMSE table above only if space permits; assign its number after the existing chapter tables. Do not add the runtime/memory table to the main chapter because Python and compiled-C++ workloads differ.

Paste these two short paragraphs:

The three estimators were evaluated on the UrbanNav-HK-Deep-Urban-1 and UrbanNav-HK-Medium-Urban-1 ground-vehicle sequences [23]. B1 is a GNSS/IMU ESKF, B2 adds NIS-based observation rejection, and B3 uses IMU preintegration in a 5 s GNSS/IMU factor graph. The estimators use the same observations, initial state, noise settings and evaluation epochs. Position errors are measured against the provided reference trajectories without fitted trajectory alignment.

Figures 3.9 and 3.10 show that the relative performance depends on the sequence. NIS gating reduces the 3D RMSE by 10.5% on Deep-Urban-1, and increases it by 75.5% on Medium-Urban-1. The corresponding B3 RMSE values are 98.53 m and 34.52 m. Residual errors remain. These results illustrate the effects of observation rejection and window-based estimation, rather than establishing a general ranking or UAV flight performance.

Suggested captions:

Figure 3.9  Three-dimensional position errors on UrbanNav-HK-Deep-Urban-1. B1: ESKF; B2: ESKF with NIS gating; B3: GNSS/IMU fixed-lag factor graph. The vertical axis uses a logarithmic scale.

Figure 3.10  Three-dimensional position errors on UrbanNav-HK-Medium-Urban-1. The methods and evaluation settings are the same as in Figure 3.9. The vertical axis uses a logarithmic scale.

Copy paragraph styles from the existing 1.4.1 body, and copy caption style and spacing from the existing figure captions. Insert images inline at about 11.5 cm width, preserving aspect ratio. PNG files are 300 dpi; PDF files embed Times New Roman for vector export. Do not turn these paragraphs into new heading levels. This Markdown supplies content and placement; the original Word file has not been changed.

## References and scope

In the inspected Word file, [23] is UrbanNav, [2] and [3] cover estimation/filtering, [7] covers GNSS/INS FGO versus EKF, and [16] covers improved inertial preintegration. Reuse these references where appropriate. The new data paragraph introduces the already-listed [23] earlier, in 1.4.5, after the existing first citation of [22] in 1.4.3 and before [24]. The numbered reference order therefore stays unchanged, and no new paper is needed. These are newly measured outputs, not numbers copied from [7].

GTSAM 4.2 and RTKLIB 2.4.3 b34 are acknowledged with official links and versions in the repository. Native KF-GINS was not executed, so do not add its paper while describing these results as a KF-GINS reproduction. If iSAM2 itself is explained in new theoretical text, cite its original method paper rather than presenting that method as new. If a revised manuscript has already renumbered the references, match the UrbanNav citation by title before pasting.

Before publication, check the existing IMU-preintegration equations against the corrected source text: the velocity summand must use the intermediate rotation indexed by the IMU sample, the second-order position term must include the bias-corrected specific force, and the gravity term must use the squared full keyframe interval. The executable implementation does not use those transcription errors. This note does not change the original document.
