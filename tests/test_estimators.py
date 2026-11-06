"""Physics, gating and Jacobian checks; no dataset ground truth is used."""
import json
from pathlib import Path
import unittest
import numpy as np
from algorithms.common import State, exp, initial_state
from algorithms.B1_ESKF import ESKF
from algorithms.B2_ESKF_NIS import GatedESKF

CFG = json.loads((Path(__file__).resolve().parents[1]/"configs/benchmark.json").read_text())


def zero_state():
    return State(np.zeros(3), np.zeros(3), np.eye(3), np.zeros(3), np.zeros(3))


class EstimatorChecks(unittest.TestCase):
    def test_stationary_gravity_and_covariance(self):
        f = ESKF(zero_state(), CFG)
        samples = np.tile([0, 0, 0, 0, 0, CFG["gravity_mps2"]], (200, 1))
        f.propagate(samples, .01)
        np.testing.assert_allclose(f.s.p, 0, atol=1e-10)
        np.testing.assert_allclose(f.s.v, 0, atol=1e-10)
        self.assertGreater(np.linalg.eigvalsh(f.P).min(), 0)

    def test_gate_and_disabled_gate_equivalence(self):
        b1, b2 = ESKF(zero_state(), CFG), GatedESKF(zero_state(), CFG)
        measurement = np.array(CFG["antenna_lever_body_m"])+[.1, -.2, .3]
        cov = np.eye(3)*9
        b1.update(measurement, cov)
        b2.update(measurement, cov, threshold=np.inf)
        np.testing.assert_allclose(b1.s.p, b2.s.p, atol=1e-12)
        np.testing.assert_allclose(b1.P, b2.P, atol=1e-12)
        prior = b2.s.copy()
        self.assertFalse(b2.update(measurement+1000, cov))
        np.testing.assert_array_equal(prior.p, b2.s.p)

    def test_constant_turn_mechanization(self):
        s = zero_state()
        speed, rate, duration = 3., .1, 20.
        s.v[1] = speed
        f = ESKF(s, CFG)
        samples = np.tile([0, 0, rate, -speed*rate, 0, CFG["gravity_mps2"]], (2000, 1))
        f.propagate(samples, .01)
        angle = rate*duration
        expected = np.array([-speed/rate*(1-np.cos(angle)), speed/rate*np.sin(angle), 0])
        np.testing.assert_allclose(f.s.p, expected, atol=2e-5)
        np.testing.assert_allclose(f.s.R, exp(np.array([0, 0, angle])), atol=1e-10)

    def test_initialization_is_causal(self):
        t = 10000.+np.arange(151)
        data = {"epoch_t": t, "gnss_p": np.column_stack((t-t[0], np.zeros((151, 2)))),
                "imu_t": np.arange(t[0], t[-1], .01),
                "imu": np.tile([0, 0, 0, 0, 0, CFG["gravity_mps2"]], (15000, 1))}
        a, first = initial_state(data, CFG)
        data["gnss_p"][a+1:] += 10000
        b, second = initial_state(data, CFG)
        self.assertEqual(a, b)
        for k in ["p", "v", "R", "bg", "ba"]:
            np.testing.assert_array_equal(getattr(first, k), getattr(second, k))

    def test_antenna_factor_jacobian(self):
        import gtsam as gt
        from functools import partial
        from algorithms.B3_GNSS_IMU_FGO.fixed_lag import antenna_error
        lever = np.array(CFG["antenna_lever_body_m"])
        pose = gt.Pose3(gt.Rot3(exp(np.array([.1, -.2, .4]))), np.array([4., 5., 6.]))
        k = gt.symbol("x", 0)
        factor = gt.CustomFactor(gt.noiseModel.Isotropic.Sigma(3, 1), [k],
                                partial(antenna_error, lever, np.ones(3)))
        values = gt.Values()
        values.insert(k, pose)
        H = [None]
        antenna_error(lever, np.ones(3), factor, values, H)
        numeric = np.zeros((3, 6))
        for j in range(6):
            d = np.zeros(6)
            d[j] = 1e-6
            pp, pm = pose.retract(d), pose.retract(-d)
            numeric[:, j] = ((pp.translation()+pp.rotation().matrix()@lever)-
                              (pm.translation()+pm.rotation().matrix()@lever))/(2e-6)
        np.testing.assert_allclose(H[0], numeric, atol=2e-8)

    def test_fixed_lag_marginalization_stationary(self):
        from algorithms.B3_GNSS_IMU_FGO import FixedLagGNSSIMU
        f = FixedLagGNSSIMU(zero_state(), CFG, 0.)
        samples = np.tile([0, 0, 0, 0, 0, CFG["gravity_mps2"]], (100, 1))
        lever = np.array(CFG["antenna_lever_body_m"])
        for i in range(1, 9):
            s = f.step(samples, .01, float(i), lever, np.eye(3)*9)
        np.testing.assert_allclose(s.p, 0, atol=1e-6)
        np.testing.assert_allclose(s.v, 0, atol=1e-6)
        self.assertLessEqual(f.smoother.calculateEstimate().size(), 18)

    def test_fixed_lag_motion_and_gnss_reacquisition(self):
        from algorithms.B3_GNSS_IMU_FGO import FixedLagGNSSIMU
        s = zero_state()
        s.v[:] = [2., 1., 0.]
        f = FixedLagGNSSIMU(s, CFG, 0.)
        samples = np.tile([0, 0, 0, 0, 0, CFG["gravity_mps2"]], (100, 1))
        lever = np.array(CFG["antenna_lever_body_m"])
        for i in range(1, 25):
            observed = i < 4 or i > 18
            state = f.step(samples, .01, float(i), s.v*i+lever if observed else None,
                           np.eye(3)*9 if observed else None)
        np.testing.assert_allclose(state.p, s.v*24, atol=2e-5)
        np.testing.assert_allclose(state.v, s.v, atol=2e-5)


if __name__ == "__main__":
    unittest.main()
