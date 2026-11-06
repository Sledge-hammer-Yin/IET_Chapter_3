"""Causal GTSAM 4.2 iSAM2 fixed-lag GNSS/IMU optimization."""
import numpy as np
import gtsam as gt
import gtsam_unstable as gu
from functools import partial
from algorithms.common import State, skew


def key(c, i):
    return gt.symbol(c, i)


def antenna_error(lever, measurement, this, values, H):
    pose = values.atPose3(this.keys()[0])
    R = pose.rotation().matrix()
    if H is not None:
        H[0] = np.asfortranarray(np.column_stack((-R@skew(lever), R)))
    return pose.translation()+R@lever-measurement


class FixedLagGNSSIMU:
    def __init__(self, state, cfg, time):
        self.cfg, self.s, self.k = cfg, state.copy(), 0
        self.updates, self.cost = 0, 0.
        params = gt.ISAM2Params()
        params.setRelinearizeThreshold(cfg["isam_relinearize_threshold"])
        params.relinearizeSkip = cfg["isam_relinearize_skip"]
        params.setFactorization(cfg["linear_solver"])
        params.findUnusedFactorSlots = True
        self.smoother = gu.IncrementalFixedLagSmoother(cfg["fixed_lag_seconds"], params)
        self.params = gt.PreintegrationParams.MakeSharedU(cfg["gravity_mps2"])
        self.params.setAccelerometerCovariance(np.eye(3)*cfg["acc_noise_density"]**2)
        self.params.setGyroscopeCovariance(np.eye(3)*cfg["gyro_noise_density"]**2)
        self.params.setIntegrationCovariance(np.eye(3)*1e-8)
        graph, values, stamps = self.containers(state, time)
        sig = np.r_[np.radians([cfg["tilt_prior_sigma_deg"]]*2+
                              [cfg["yaw_prior_sigma_deg"]]),
                    [cfg["position_prior_sigma_m"]]*3]
        graph.add(gt.PriorFactorPose3(key("x", 0), self.pose(state),
                                     gt.noiseModel.Diagonal.Sigmas(sig)))
        graph.add(gt.PriorFactorVector(key("v", 0), state.v,
                  gt.noiseModel.Isotropic.Sigma(3, cfg["velocity_prior_sigma_mps"])))
        bs = np.r_[[cfg["acc_bias_prior_sigma"]]*3,
                   [cfg["gyro_bias_prior_sigma"]]*3]
        graph.add(gt.PriorFactorConstantBias(key("b", 0), self.bias(state),
                                           gt.noiseModel.Diagonal.Sigmas(bs)))
        self.smoother.update(graph, values, stamps)

    @staticmethod
    def pose(s):
        return gt.Pose3(gt.Rot3(s.R), s.p)

    @staticmethod
    def bias(s):
        return gt.imuBias.ConstantBias(s.ba, s.bg)

    def containers(self, state, time):
        graph, values = gt.NonlinearFactorGraph(), gt.Values()
        stamps = gu.FixedLagSmootherKeyTimestampMap()
        for c, value in [("x", self.pose(state)), ("v", state.v),
                         ("b", self.bias(state))]:
            values.insert(key(c, self.k), value)
            stamps.insert((key(c, self.k), float(time)))
        return graph, values, stamps

    def step(self, samples, dt, time, position=None, covariance=None):
        previous = self.k
        bias = self.bias(self.s)
        pim = gt.PreintegratedImuMeasurements(self.params, bias)
        for sample in samples:
            pim.integrateMeasurement(sample[3:], sample[:3], dt)
        predicted = pim.predict(gt.NavState(self.pose(self.s), self.s.v), bias)
        initial = State(predicted.position(), predicted.velocity(),
                        predicted.attitude().matrix(), self.s.bg, self.s.ba)
        self.k += 1
        graph, values, stamps = self.containers(initial, time)
        graph.add(gt.ImuFactor(key("x", previous), key("v", previous),
                              key("x", self.k), key("v", self.k),
                              key("b", previous), pim))
        sig = np.r_[[self.cfg["acc_bias_random_walk"]]*3,
                    [self.cfg["gyro_bias_random_walk"]]*3]*np.sqrt(len(samples)*dt)
        graph.add(gt.BetweenFactorConstantBias(
            key("b", previous), key("b", self.k), gt.imuBias.ConstantBias(),
            gt.noiseModel.Diagonal.Sigmas(sig)))
        if position is not None:
            error = partial(antenna_error,
                            np.array(self.cfg["antenna_lever_body_m"]), position)
            graph.add(gt.CustomFactor(gt.noiseModel.Gaussian.Covariance(covariance),
                                      [key("x", self.k)], error))
        self.smoother.update(graph, values, stamps)
        for _ in range(self.cfg["extra_relinearization_updates"]):
            self.smoother.update(gt.NonlinearFactorGraph(), gt.Values(),
                                 gu.FixedLagSmootherKeyTimestampMap())
        self.updates = 1+self.cfg["extra_relinearization_updates"]
        result = self.smoother.calculateEstimate()
        self.cost = self.smoother.getFactors().error(result)
        pose = result.atPose3(key("x", self.k))
        b = result.atConstantBias(key("b", self.k))
        self.s = State(pose.translation(), result.atVector(key("v", self.k)),
                       pose.rotation().matrix(), b.gyroscope(), b.accelerometer())
        return self.s
