# GLIO insertion in the chapter

The working chapter was updated in Section 1.4.6 (Section 3.4.6 in the book plan),
after the existing GLIO discussion and before the reference list.

| Figure | Content | Experiment file |
|---|---|---|
| 3.14 | Three-dimensional position errors | comparison_position_error.png |
| 3.15 | Horizontal trajectories | comparison_trajectory.png |

Files are in `results/GLIO/Deep-Urban-1/Comparison_calibrated_v2` from the repository root.
Two body paragraphs introduce the three modes and interpret their measured results.
Existing paragraph, figure and caption styles were reused. No heading, equation,
reference entry or existing image was changed. Original material is retained in
the chapter's adjacent backups folder, outside the publication repository.

| Method | Horizontal RMSE (m) | 3D RMSE (m) |
|---|---:|---:|
| LC | 3.590 | 5.912 |
| TC-Pose | 1.820 | 4.547 |
| TC-Surface | 1.622 | 3.508 |

These values use 1514 common reference epochs, with 99.87% coverage of the
eligible interval, a shared supplied initialization prior and no fitted alignment.
The report documents implementation corrections, the frozen adjacent-attitude
lever approximation and reference-quality groups. The case uses ground-vehicle
data. It is not a UAV flight validation or a combined ranking against B1-B3.

## Inserted text

Three GLIO-based configurations were evaluated on the UrbanNav-HK-Deep-Urban-1 ground-vehicle sequence [12,23]. LC combines GNSS position solutions with LiDAR/IMU odometry. TC-Pose uses double-difference pseudorange with relative pose constraints, while TC-Surface uses LiDAR surface constraints in the batch optimization. All three use the same GNSS, LiDAR and IMU data, sensor extrinsics and author-supplied position and attitude priors. The implementation was corrected to enable the LC GNSS input and apply the antenna lever arm. In these runs, the shared front end uses LiDAR/IMU, and the TC batch graphs use L1 double-difference pseudorange; Doppler factors are disabled. The TC antenna offset is held fixed at a selected adjacent estimated attitude during factor assembly.

Figures 3.14 and 3.15 show the three-dimensional position errors and horizontal trajectories. Evaluation uses 1514 common 1 Hz reference epochs after a 20 s settling interval, covering 99.87% of the eligible interval. Each estimate is transferred to the SPAN-CPT reference point using its own estimated attitude, without fitted trajectory or time alignment. The horizontal RMSEs of LC, TC-Pose and TC-Surface are 3.59 m, 1.82 m and 1.62 m; their three-dimensional RMSEs are 5.91 m, 4.55 m and 3.51 m. LC accepts 14 GNSS position factors under the existing observation gates. These single-sequence results illustrate the three configurations under the stated conditions. They do not establish general superiority or UAV flight performance. Their inputs and evaluation settings differ from B1-B3, so the two groups are evaluated separately.
