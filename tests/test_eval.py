import numpy as np
from eval.calibrate import cp_upper, fit_recalibrator, pick_allow_threshold
from eval.run_h1 import auroc_ci, paired_diff_ci
from reflexarc.authority import promote


def test_cp_upper_bounds():
    # 0 events in 100 trials at 95% confidence should be around ~0.03
    bound = cp_upper(0, 100, conf=0.95)
    assert 0.02 < bound < 0.04
    assert cp_upper(100, 100) == 1.0


def test_authority_promotion():
    # Under n_min, stays in shadow
    assert promote("read_only", 100, 0, "shadow", n_min=300) == "shadow"
    # Reaching n_min promotes to restrict
    assert promote("read_only", 300, 0, "shadow", n_min=300) == "restrict"
    # Zero false allows in 300 trials promotes to grant
    assert promote("read_only", 300, 0, "restrict", budget=0.01, n_min=300) == "grant"
    # Too many false allows stays at restrict
    assert promote("read_only", 300, 10, "restrict", budget=0.01, n_min=300) == "restrict"


def test_auroc_ci():
    y = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    score = np.array([0.1, 0.2, 0.3, 0.4, 0.7, 0.8, 0.9, 1.0])
    point, ci = auroc_ci(y, score, n_boot=200)
    assert point == 1.0
    assert ci[0] >= 0.8
