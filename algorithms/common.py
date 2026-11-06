"""Shared geometry and causal initialization. No ground truth is used here."""
from dataclasses import dataclass
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.optimize import least_squares


def skew(v):
    x, y, z = v
    return np.array([[0., -z, y], [z, 0., -x], [-y, x, 0.]])


def exp(v):
    return Rotation.from_rotvec(v).as_matrix()


def lla_ecef(lat, lon, height):
    lat, lon = np.radians(lat), np.radians(lon)
    a, e2 = 6378137., 6.6943799901413165e-3
    n = a / np.sqrt(1 - e2 * np.sin(lat)**2)
    return np.column_stack(((n+height)*np.cos(lat)*np.cos(lon),
                            (n+height)*np.cos(lat)*np.sin(lon),
                            (n*(1-e2)+height)*np.sin(lat)))


def ecef_frame(origin):
    """ECEF to local ENU; the origin comes from GNSS, not reference data."""
    x, y, z = origin
    lon = np.arctan2(y, x)
    lat = np.arctan2(z, np.hypot(x, y)*(1-6.6943799901413165e-3))
    for _ in range(8):
        n = 6378137./np.sqrt(1-6.6943799901413165e-3*np.sin(lat)**2)
        lat = np.arctan2(z+6.6943799901413165e-3*n*np.sin(lat), np.hypot(x, y))
    s, c, sl, cl = np.sin(lat), np.cos(lat), np.sin(lon), np.cos(lon)
    return np.array([[-sl, cl, 0], [-s*cl, -s*sl, c], [c*cl, c*sl, s]])


@dataclass
class State:
    p: np.ndarray
    v: np.ndarray
    R: np.ndarray
    bg: np.ndarray
    ba: np.ndarray

    def copy(self):
        return State(*(x.copy() for x in (self.p, self.v, self.R, self.bg, self.ba)))


def initial_state(data, cfg):
    """Use past GNSS, gravity tilt and an initial forward-motion convention.

    The body axes are right/forward/up. The vehicle-forward assumption is
    initialization only, shared by all methods; no nonholonomic update is used.
    """
    times = data["epoch_t"]
    valid = np.isfinite(data["gnss_p"]).all(axis=1)
    earliest = np.flatnonzero(valid)[0]
    start = max(earliest + int(cfg["bootstrap_seconds"]),
                int(np.searchsorted(times, times[0]+cfg["bootstrap_seconds"])))
    # A minimum bootstrap duration is not enough if GNSS is initially missing.
    # Wait causally for five recent fixes and observable horizontal motion.
    while start < len(times)-20:
        history = np.flatnonzero(valid & (times <= times[start]) &
                                 (times >= times[start]-30.))
        if len(history) >= 5 and np.linalg.norm(
                data["gnss_p"][history[-1], :2]-data["gnss_p"][history[0], :2]) >= 10:
            break
        start += 1
    else:
        raise ValueError("Insufficient recent GNSS motion for causal initialization.")
    dt = times[history]-times[start]
    positions = data["gnss_p"][history]
    design = np.column_stack((np.ones(len(dt)), dt))
    beta = np.linalg.lstsq(design, positions, rcond=None)[0]
    fit = least_squares(lambda b: (design@b.reshape(2, 3)-positions).ravel(),
                        beta.ravel(), loss="soft_l1", f_scale=5.)
    pos, vel = fit.x.reshape(2, 3)
    if np.linalg.norm(vel[:2]) < .8:
        delta = positions[-1]-positions[0]
        if np.linalg.norm(delta[:2]) < 10:
            raise ValueError("GNSS heading is not observable during bootstrap.")
        vel[:2] = delta[:2]/max(dt[-1]-dt[0], 1.)
    imu_early = data["imu"][data["imu_t"] < times[0]+3.]
    force = np.median(imu_early[:, 3:], axis=0)
    unit = force/np.linalg.norm(force)
    axis = np.cross(unit, np.array([0., 0., 1.]))
    tilt = np.eye(3)+skew(axis)+skew(axis)@skew(axis)/(1+unit[2])
    forward = tilt@np.array([0., 1., 0.])
    heading = np.arctan2(vel[1], vel[0])-np.arctan2(forward[1], forward[0])
    R = exp(np.array([0., 0., heading]))@tilt
    # Do not infer a gyroscope bias from a potentially moving interval.
    bg = np.zeros(3)
    if np.max(np.std(imu_early[:, :3], axis=0)) < .01:
        bg = np.mean(imu_early[:, :3], axis=0)
    state = State(pos-R@np.array(cfg["antenna_lever_body_m"]),
                  vel, R, bg, np.zeros(3))
    return start, state


def interval_samples(data, t0, t1):
    a, b = np.searchsorted(data["imu_t"], [t0-1e-5, t1-1e-5])
    return data["imu"][a:b].astype(float), 1./float(data["imu_rate_hz"])
