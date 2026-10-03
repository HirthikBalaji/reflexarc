from __future__ import annotations

from scipy.stats import beta


def cp_upper(k: int, n: int, conf: float = 0.95) -> float:
    """One-sided Clopper-Pearson exact upper confidence bound on a binomial proportion."""
    if n <= 0:
        return 1.0
    if k >= n:
        return 1.0
    return float(beta.ppf(conf, k + 1, n - k))


def promote(
    category: str,
    would_allow_audited: int,
    false_allows: int,
    current: str,
    budget: float = 0.01,
    n_min: int = 300,
) -> str:
    """Evaluate earned authority promotion under rigorous empirical bounds.

    - shadow -> restrict: Requires at least n_min observations with zero unhandled critical faults.
    - restrict -> grant: Requires false-allow rate upper bound (at 95% confidence) <= budget.
    """
    if current == "shadow" and would_allow_audited >= n_min:
        return "restrict"

    if current == "restrict" and would_allow_audited >= n_min:
        bound = cp_upper(false_allows, would_allow_audited, conf=0.95)
        if bound <= budget:
            return "grant"

    return current
