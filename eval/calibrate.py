import numpy as np
from scipy.stats import beta
from sklearn.isotonic import IsotonicRegression


def cp_upper(k: int, n: int, conf: float = 0.95) -> float:
    """One-sided Clopper-Pearson upper bound on a rate, k events in n trials."""
    return 1.0 if k >= n else float(beta.ppf(conf, k + 1, n - k))


def fit_recalibrator(p: np.ndarray, y: np.ndarray) -> IsotonicRegression:
    """Fit isotonic regression to recalibrate raw probabilities."""
    return IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0).fit(p, y)


def pick_allow_threshold(
    p: np.ndarray,
    y: np.ndarray,
    budget: float = 0.01,
    n_min: int = 50,
    conf: float = 0.95,
) -> float:
    """Largest threshold t such that true-hazard rate's upper bound stays under budget."""
    order = np.argsort(p)
    p_sorted, y_sorted = p[order], y[order].astype(int)
    best = 0.0
    for i in range(n_min, len(p_sorted) + 1):
        if cp_upper(int(y_sorted[:i].sum()), i, conf) <= budget:
            best = float(p_sorted[i - 1])
    return best
