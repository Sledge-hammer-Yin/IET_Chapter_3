# Models and common evaluation

## Shared inputs

Use only the Xsens gyroscope and accelerometer and the selected u-blox F9P RINEX stream. Receiver observations, HKSC base observations and broadcast navigation data are converted by RTKLIB 2.4.3 b34 into forward L1 DGNSS positions. A separately computed forward SPP position is used only when the DGNSS position is unavailable. No backward or combined solution is used. The enabled constellation mask is 125, subject to the satellites available in the downloaded RINEX files. Neither carrier-phase RTK integer fixing nor raw-pseudorange tight coupling is used by B1--B3.

The ROS `field.header.stamp` is the IMU UTC timestamp; `%time` is not used. RTKLIB exports UTC through `-u`. Reference timestamps are already Unix UTC. The adapter averages all raw measurements in each 10 ms bin, giving shared 100 Hz input. It does not merely select every fourth sample. Both actual sequences have zero empty bins. The adapter would fill at most two adjacent empty bins by interpolation and rejects larger gaps.

Navigation states use metres, seconds, radians, and an ENU frame whose origin is the first available GNSS position. Body axes are right, forward and up. Calibration translations are interpreted as the following body-frame lever vectors:

\[
\mathbf{l}_{g}=[0,\;0.86,\;-0.31]^{\mathsf T}\;\mathrm{m},\qquad
\mathbf{l}_{r}=[0,\;0,\;0.14]^{\mathsf T}\;\mathrm{m}.
\]

The same explicit convention is used in all estimators: the GNSS antenna position is \(\mathbf{p}+\mathbf{R}\mathbf{l}_{g}\), and the reference-point output is \(\mathbf{p}+\mathbf{R}\mathbf{l}_{r}\). The supplied antenna translation is manually measured, with an indicated uncertainty of about 0.1 m. The present comparison is not a calibration validation or a centimetre-accuracy claim.

Initial tilt comes from the median specific force over the first 3 s. Initial yaw and velocity come from a robust straight-line fit to past GNSS positions over 30 s, assuming the vehicle body-forward axis follows horizontal motion. A mean initial gyro bias is used only if the early gyro standard deviation is below 0.01 rad/s on all axes. Initial acceleration bias is zero. The minimum bootstrap is 60 s after the first available GNSS epoch; initialization waits longer if there are fewer than five recent fixes or less than 10 m of horizontal displacement. All methods receive exactly the same initial state and prior standard deviations. No reference position, velocity, attitude or IMU quaternion is used by the estimators. No zero-velocity, vehicle nonholonomic, Doppler, learned or map constraint is added.

## B1 and B2

The nominal state is \((\mathbf{p},\mathbf{v},\mathbf{R},\mathbf{b}_{g},\mathbf{b}_{a})\). The 15-dimensional ESKF error order is

\[
\delta\mathbf{x}=[\delta\mathbf{p}^{\mathsf T},\;\delta\mathbf{v}^{\mathsf T},\;
\delta\boldsymbol{\theta}^{\mathsf T},\;\delta\mathbf{b}_{g}^{\mathsf T},\;
\delta\mathbf{b}_{a}^{\mathsf T}]^{\mathsf T},\qquad
\mathbf{R}^{+}=\mathbf{R}^{-}\operatorname{Exp}(\delta\boldsymbol{\theta}).
\]

B1 uses midpoint nominal propagation, a second-order transition-matrix approximation, continuous white-noise/bias-random-walk covariance, a position-and-lever-arm GNSS measurement, Joseph covariance update and error reset. The local model uses fixed gravity and omits Earth rotation, transport rate and scale-factor states. These omissions limit the comparison with full geodetic INS implementations and the improved preintegration model in chapter reference [16].

B2 adds only an NIS gate. For innovation \(\boldsymbol{\nu}_{i}\), innovation covariance \(\mathbf{S}_{i}\), and probability \(\alpha=0.999\), accept the update if

\[
q_i=\boldsymbol{\nu}_{i}^{\mathsf T}\mathbf{S}_{i}^{-1}\boldsymbol{\nu}_{i}
\leq \chi^2_{3,\alpha}\approx16.27.
\]

The NIS calculation uses the estimator's predicted covariance, not reference errors. This simple rejection gate has no automatic covariance adaptation or reacquisition reset. It can reject useful observations after drift. A statistical threshold does not establish calibrated consistency under urban multipath.

## B3

At each 1 Hz epoch, B3 introduces pose, velocity and bias variables. GTSAM preintegrates the same 100 Hz samples between consecutive epochs. The graph contains initial priors, inertial factors, bias-random-walk factors and GNSS antenna-position factors. The GNSS residual is

\[
\mathbf{r}_{g,i}=\mathbf{p}_i+\mathbf{R}_i\mathbf{l}_g-\mathbf{z}_{g,i}.
\]

The squared, covariance-weighted residuals and prior define the Gaussian MAP objective. Its active window is 5 s; at 1 Hz this retains up to six state epochs. Marginalization carries earlier information into a prior. iSAM2 uses QR, threshold 0.01, skip 1, and three extra relinearization updates after inserting each epoch. Slot reuse prevents unbounded factor-storage growth. This provides an incremental approximate MAP solution, without a global-optimum guarantee. No robust loss or observation gate is applied. Only the current estimate at its own timestamp is scored; later revisions to older states are not exported as if they were causal outputs.

GTSAM Pose3 uses rotation-then-translation local coordinates, while B1 stores position-first additive ENU errors. The initial physical uncertainties are equal: the position prior is isotropic, so its rotated Pose3 local translation covariance represents the same position uncertainty. Covariance ordering is deliberately adapted rather than copied between incompatible state layouts.

## Metrics and fairness

The reference files are the official 1 Hz SPAN-CPT/IE trajectories. Latitude, longitude and ellipsoidal height are converted to the same ENU frame. Estimates and reference are matched in UTC to within 2 ms. There is no fitted rotation, translation, scale or time shift. No method-specific epoch deletion or reference-quality filtering is applied. Reference quality codes vary and are retained in the manifests; uniform centimetre-level truth accuracy is not assumed.

Discard the common initialization interval and then 30 s of settling. Let \(\mathcal{E}\) be the remaining common matched epoch set, \(n=|\mathcal{E}|\), and

\[
\mathbf{e}_i=\widehat{\mathbf{p}}^{\mathrm{ref}}_i-\mathbf{p}^{\mathrm{ref}}_i,\qquad
\mathrm{RMSE}_{3D}=\sqrt{\frac{1}{n}\sum_{i\in\mathcal{E}}\|\mathbf{e}_i\|^2}.
\]

Horizontal RMSE uses the east/north components, vertical RMSE uses the up component, and 3D P95 and maximum use \(\|\mathbf{e}_i\|\). The reported 10 s relative translation RMSE is

\[
\mathrm{RPE}_{10s}=\sqrt{\frac{1}{|\mathcal{D}|}\sum_{i\in\mathcal{D}}
\|\mathbf{e}_{i+10}-\mathbf{e}_i\|^2},\qquad
\mathcal{D}=\{i:i\in\mathcal{E},\;i+10\in\mathcal{E}\}.
\]

This is a translation-increment measure on the 1 Hz grid, not a full SE(3) relative-pose error. Rotation truth is not evaluated. Output coverage measures finite outputs during the matched scoring interval. The evaluated fraction of the full input timeline is also reported, so 100% post-initialization coverage is not confused with immediate startup availability.

Estimator time includes integration and updates for each 1 s input interval, without data parsing, plotting, file writing or reference evaluation. Memory is the maximum process RSS sampled at 1 Hz, in MiB; it is not an exact OS peak or graph-only allocation. Each method runs in a fresh process, with one numerical-library thread. B1/B2 propagation loops are Python; B3's main numerical work is compiled C++. Timing therefore compares these implementations on this machine, not the inherent speed of the mathematical methods. All reported accuracy statistics describe these two sequences and this fixed configuration only.

