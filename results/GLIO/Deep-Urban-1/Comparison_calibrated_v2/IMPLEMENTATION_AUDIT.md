# Controlled GLIO implementation audit

Profile: `calibrated_v2`, based on upstream commit
`332d19ff641f2ada9d9d75f2a6dab013d6015f76`. The exact source changes are in
`source.patch`; hashes and shared settings are in `protocol.json`.

## Geometry and initialization

| Item | Shared setting | Basis |
|---|---|---|
| LiDAR pose in IMU coordinates | Identity rotation; [0, 0, 0.28] m | Dataset extrinsics and upstream GLIO preset agree |
| Antenna position in IMU coordinates | [0, 0.86, -0.31] m | Dataset's antenna-to-IMU transform, interpreted consistently with its LiDAR-to-IMU convention |
| SPAN reference point in IMU coordinates | [0, 0, 0.14] m | `body_T_SPAN` |
| Initial ECEF anchor | [-2419233.42, 5385473.13, 2405341.30] m | Shared supplied GLIO prior |
| Initial roll, pitch, yaw | [0.6825, 0.098, 60.8] degrees | Shared supplied GLIO prior |
| Initial velocity, accelerometer bias, gyro bias | All zero | Upstream initialization code |
| Gravity | 9.80511 m/s^2 | Shared GLIO preset |

The initial anchor and attitude are supplied priors. Their original derivation is
unverified, so initialization accuracy is not tested here. Reference positions and
attitudes are never used by the online estimator. The output transfer to the SPAN
point uses each method's estimated attitude, not the reference attitude.

The shared IMU model retains the GLIO preset (`acc_n=0.003993957088823881`,
`gyr_n=0.0015636343949698187`, `acc_w=0.00006435665935353257`,
`gyr_w=0.00003564031869636761`). The public Xsens Allan file has different
average-axis numbers. Those are not silently substituted without a separate noise
model/unit analysis. This is a declared common model, not a new sensor-noise fit.

## Active paths and necessary fixes

1. `rtklibOdomHandler` fills `GNSSQueue` only inside `if (RTKinLocal)`.
   All three configurations now set that flag true. The LC run must also produce
   a nonempty `lc_gnss_factors.csv`, proving actual accepted GNSS position factors.
2. The active TC batch DD factor hard-coded a zero antenna lever arm. It now accepts
   the estimated-attitude offset supplied by the batch caller. The LC GPS point is
   transferred from the antenna to the IMU using the current estimated orientation.
3. The RNG reads `GLIO_RANDOM_SEED=42` for controlled feature sampling. Hardware-entropy
   defaults remain available when that variable is absent. Asynchronous execution
   can still cause run-to-run differences; one trial per mode is not a significance test.
4. The shared sliding-window GNSS block is disabled by upstream `#if 0`.
   The TC batch DD pseudorange block is active; batch Doppler is disabled.
   An apparent station-position issue in the disabled sliding-window helper is
   not an active residual in this experiment and has not been modified.

The DD factor's anchor and local yaw parameter blocks are held constant by the
estimator. Its position Jacobians were checked against numerical derivatives.
The maximum observed discrepancy was approximately 3.05e-7; antenna geometry,
nonzero-lever sensitivity and fixed-seed checks also passed. Evaluator checks cover
SPAN-point transfer, WGS84/ENU axes, known translation errors, relative-displacement
pairs, exact-time samples and interpolation-gap boundaries.

## Frozen-attitude approximation clarification

The frozen profile manifest originally describes the TC lever rotation as the
"nearest" estimated attitude. The source actually retains the repository's adjacent
pose-selection expression, `ratio < 0.5 ? left : right`, with
`ratio = (upper_time - observation_time) / (upper_time - lower_time)`.
That expression is not guaranteed to select the nearest pose. The accurate
description is **a selected adjacent estimated attitude, frozen during factor
assembly**. This wording clarification changes no data, code, parameter, or hash
after the protocol was frozen. The final report uses the accurate description.

This approximation is explicitly retained rather than represented as continuous
attitude interpolation or a full rotational lever-arm Jacobian model. It limits
claims about absolute accuracy and exact paper reproduction. All TC variants use
the same implementation rule, and the public antenna translation itself is only
manually measured (reported uncertainty about 0.1 m).

## Scope

The experiments compare three documented GLIO-based configurations on one ground
vehicle sequence. Observation forms, gating and graph structures differ by design.
They do not isolate solver choice alone, establish a UAV flight result, or replace
the separate B1-B3 filtering/optimization comparison. The old zero-lever-arm and
short-run results are excluded from the new common-epoch statistics.

Sources: [GLIO](https://github.com/XikunLiu-huskit/GLIO),
[Deep-Urban-1 calibration](https://github.com/IPNL-POLYU/UrbanNavDataset/blob/master/UrbanNav-HK-Deep-Urban-1/extrinsic.yaml),
[Xsens calibration file](https://github.com/IPNL-POLYU/UrbanNavDataset/blob/master/UrbanNav-HK-Deep-Urban-1/xsens_imu_param.yaml).
