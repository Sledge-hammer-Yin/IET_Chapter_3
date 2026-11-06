# Shared settings

`benchmark.json` is used unchanged for both sequences and all three methods. Noise values are rounded from the official Xsens average-axis calibration: acceleration noise 0.01120, gyroscope noise 0.01027, acceleration-bias random walk 0.000118, and gyroscope-bias random walk 0.0000914. They are treated as continuous-time noise amplitudes; their squared values enter the process covariances. This interpretation is an explicit modeling assumption.

GNSS covariance is rotated from ECEF into ENU. Its eigenvalues are floored at (3 m)^2 for DGNSS and (6 m)^2 for SPP. These conservative fixed floors are not fitted to reference errors. The policy uses a DGNSS fix whenever available, otherwise an SPP fix, otherwise IMU-only propagation. It does not choose whichever fix happens to be closer to the reference.

RTKLIB uses the explicit navigation-system mask 125: GPS, GLONASS, Galileo, QZSS, BeiDou and NavIC are enabled where the RINEX files supply the required observations and ephemerides. This is not a GPS-only frontend. The adapter writes the mask into `data/processed/<sequence>/rtklib.conf` and saves the exact commands. It avoids RTKLIB 2.4.3 b34's fall-through behavior in the `-sys` command-line switch. A new `pos1-navsys` value requires rebuilding the GNSS solutions; the saved command/configuration check handles this automatically.

Position, velocity, tilt, yaw and bias prior standard deviations are shared. The common bootstrap is at least 60 s after the first GNSS fix and waits for five recent fixes with at least 10 m horizontal displacement. The next 30 s are excluded from every method's accuracy score. The initial forward-motion assumption is appropriate for this vehicle demonstration, not a general airborne yaw initializer.

Only B2 reads `nis_probability`. Only B3 reads the window and iSAM2 settings. Change data-preparation settings through `run.py all`, or rerun `prepare` before `run`. No parameters are changed between the two evaluation sequences.

