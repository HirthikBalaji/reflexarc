import numpy as np
from sklearn.metrics import roc_auc_score


def auroc_ci(y_err, score, n_boot=2000, seed=0):
    """Compute AUROC and 95% bootstrap confidence interval."""
    rng = np.random.default_rng(seed)
    y_err, score = np.asarray(y_err), np.asarray(score)
    point = float(roc_auc_score(y_err, score))
    boots = []
    for _ in range(n_boot):
        i = rng.integers(0, len(y_err), len(y_err))
        if y_err[i].min() == y_err[i].max():
            continue
        boots.append(roc_auc_score(y_err[i], score[i]))
    ci = (
        float(np.percentile(boots, 2.5)),
        float(np.percentile(boots, 97.5)),
    )
    return point, ci


def paired_diff_ci(y_err, a, b, n_boot=2000, seed=1):
    """Bootstrap confidence interval for difference in AUROC (a vs b) on paired resamples."""
    rng = np.random.default_rng(seed)
    y_err, a, b = map(np.asarray, (y_err, a, b))
    diffs = []
    for _ in range(n_boot):
        i = rng.integers(0, len(y_err), len(y_err))
        if y_err[i].min() == y_err[i].max():
            continue
        diffs.append(roc_auc_score(y_err[i], a[i]) - roc_auc_score(y_err[i], b[i]))
    return float(np.mean(diffs)), (
        float(np.percentile(diffs, 2.5)),
        float(np.percentile(diffs, 97.5)),
    )


if __name__ == "__main__":
    print("H1 evaluation helper loaded.")
