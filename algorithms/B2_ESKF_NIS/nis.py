"""B1 with exactly one extra switch: innovation rejection."""
from scipy.stats import chi2
from algorithms.B1_ESKF import ESKF


class GatedESKF(ESKF):
    def __init__(self, state, cfg):
        super().__init__(state, cfg)
        self.threshold = float(chi2.ppf(cfg["nis_probability"], 3))

    def update(self, position, covariance, threshold=None):
        return super().update(position, covariance,
                              self.threshold if threshold is None else threshold)
