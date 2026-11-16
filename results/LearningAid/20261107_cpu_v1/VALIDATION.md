# Migration validation

Date: November 16, 2026. No model was retrained for this migration.

- All 122 saved evaluation outputs passed shape, time, finite-value and metric checks.
- All three seed-pooled summary tables matched their saved trajectories.
- GNSS solver parity, UWB filter checks and the inertial velocity Jacobian passed
  in the existing Linux CPU environment, using an isolated verification directory.
- Five freshly fetched upstream revisions matched the recorded runtime source hashes.
- The 21 model files matched their recorded checksums.
- All three single-axis figures were regenerated and visually checked on Windows.
- The original three PDF figures embed Times New Roman.
- The launcher refuses replay or training into the frozen result directory.
- Existing Section 3.4 experiment files were preserved. Section 3.6 remains reserved.

The Windows plotting launcher sets its own environment library search path.
It does not modify the existing B1-B3 environment or its installed packages.
Full neural training was not repeated. Cross-machine training determinism,
onboard timing and covariance calibration remain outside this migration.
