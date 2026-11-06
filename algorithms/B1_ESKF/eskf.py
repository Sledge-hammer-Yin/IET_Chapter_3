"""15-state right-perturbation ESKF: [dp, dv, dtheta, dbg, dba].

This is a compact independent implementation of the manuscript model, not
an execution of the native 21-state KF-GINS Phi-angle implementation.
"""
import numpy as np
from scipy.linalg import cho_factor, cho_solve
from algorithms.common import skew, exp


class ESKF:
    def __init__(self, state, cfg):
        self.s = state.copy()
        self.cfg = cfg
        self.lever = np.array(cfg["antenna_lever_body_m"])
        tilt, yaw = np.radians([cfg["tilt_prior_sigma_deg"],
                               cfg["yaw_prior_sigma_deg"]])
        sigma = np.r_[np.full(3, cfg["position_prior_sigma_m"]),
                      np.full(3, cfg["velocity_prior_sigma_mps"]),
                      tilt, tilt, yaw,
                      np.full(3, cfg["gyro_bias_prior_sigma"]),
                      np.full(3, cfg["acc_bias_prior_sigma"])]
        self.P = np.diag(sigma**2)
        self.nis = np.nan
        self.accepted = False

    def propagate(self, samples, dt):
        eye = np.eye(3)
        g = np.array([0., 0., -self.cfg["gravity_mps2"]])
        na2 = self.cfg["acc_noise_density"]**2
        ng2 = self.cfg["gyro_noise_density"]**2
        nbg2 = self.cfg["gyro_bias_random_walk"]**2
        nba2 = self.cfg["acc_bias_random_walk"]**2
        for sample in samples:
            w, a = sample[:3]-self.s.bg, sample[3:]-self.s.ba
            mid = self.s.R@exp(w*dt*.5)
            an = mid@a+g
            self.s.p += self.s.v*dt+.5*an*dt*dt
            self.s.v += an*dt
            self.s.R = self.s.R@exp(w*dt)
            F = np.zeros((15, 15))
            F[:3, 3:6] = eye
            F[3:6, 6:9] = -mid@skew(a)
            F[3:6, 12:15] = -mid
            F[6:9, 6:9] = -skew(w)
            F[6:9, 9:12] = -eye
            A = np.eye(15)+F*dt+.5*(F@F)*dt*dt
            Q = np.zeros((15, 15))
            Q[:3, :3] = eye*na2*dt**3/3
            Q[:3, 3:6] = Q[3:6, :3] = eye*na2*dt**2/2
            Q[3:6, 3:6] = eye*na2*dt
            Q[6:9, 6:9] = eye*ng2*dt
            Q[9:12, 9:12] = eye*nbg2*dt
            Q[12:15, 12:15] = eye*nba2*dt
            self.P = A@self.P@A.T+Q
        self.P = .5*(self.P+self.P.T)

    def update(self, position, covariance, threshold=np.inf):
        H = np.zeros((3, 15))
        H[:, :3] = np.eye(3)
        H[:, 6:9] = -self.s.R@skew(self.lever)
        innovation = position-self.s.p-self.s.R@self.lever
        S = H@self.P@H.T+covariance
        factor = cho_factor(S)
        self.nis = float(innovation@cho_solve(factor, innovation))
        self.accepted = self.nis <= threshold
        if not self.accepted:
            return False
        K = cho_solve(factor, H@self.P).T
        dx = K@innovation
        self.s.p += dx[:3]
        self.s.v += dx[3:6]
        self.s.R = self.s.R@exp(dx[6:9])
        self.s.bg += dx[9:12]
        self.s.ba += dx[12:15]
        J = np.eye(15)-K@H
        self.P = J@self.P@J.T+K@covariance@K.T
        reset = np.eye(15)
        reset[6:9, 6:9] = np.eye(3)-.5*skew(dx[6:9])
        self.P = reset@self.P@reset.T
        self.P = .5*(self.P+self.P.T)
        return True
