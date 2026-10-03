from reflexarc.engines import EngineOut
from reflexarc.fusion import fuse, jsd
from reflexarc.policy import Policy, decide
from reflexarc.questions import HAZARD_IDS
import numpy as np


def test_jsd():
    p = np.array([1.0, 0.0, 0.0])
    q = np.array([1.0, 0.0, 0.0])
    assert jsd(p, q) == 0.0

    p = np.array([1.0, 0.0])
    q = np.array([0.0, 1.0])
    assert jsd(p, q) > 0.99  # max divergence in bits is 1.0


def test_fuse():
    out1 = EngineOut(
        engine="e1",
        noul={h: 0.1 for h in HAZARD_IDS},
        category={"read_only": 0.9, "local_write": 0.1},
        reversibility=0.2,
        latency_ms=50.0,
    )
    out2 = EngineOut(
        engine="e2",
        noul={h: 0.2 for h in HAZARD_IDS},
        category={"read_only": 0.8, "local_write": 0.2},
        reversibility=0.4,
        latency_ms=60.0,
    )
    fused = fuse([out1, out2])
    assert fused.n_engines == 2
    assert abs(fused.p["destructive"] - 0.15) < 1e-4
    assert abs(fused.gap["destructive"] - 0.10) < 1e-4
    assert fused.category == "read_only"
    assert fused.cat_jsd < 0.1


def test_decide_rule_deny():
    pol = Policy()
    d = decide(None, "deny", 0, False, "grant", pol)
    assert d.action == "deny"
    assert "rule: deny-list" in d.reasons[0]


def test_decide_both_flag_hazard():
    pol = Policy()
    out1 = EngineOut(
        engine="e1",
        noul={h: 0.95 for h in HAZARD_IDS},
        category={"system_change": 1.0},
        reversibility=1.8,
        latency_ms=50.0,
    )
    out2 = EngineOut(
        engine="e2",
        noul={h: 0.92 for h in HAZARD_IDS},
        category={"system_change": 1.0},
        reversibility=1.9,
        latency_ms=50.0,
    )
    f = fuse([out1, out2])

    # In restrict mode, both-flag denies
    d_restrict = decide(f, "none", 0, False, "restrict", pol)
    assert d_restrict.action == "deny"

    # In shadow mode, policy does not deny directly (shadow only observes)
    d_shadow = decide(f, "none", 0, False, "shadow", pol)
    assert d_shadow.action == "escalate"


def test_decide_disagreement_escalates():
    pol = Policy()
    out1 = EngineOut(
        engine="e1",
        noul={h: 0.01 for h in HAZARD_IDS},
        category={"read_only": 1.0},
        reversibility=0.1,
        latency_ms=50.0,
    )
    # Engine 2 flags high probability -> gap is 0.89 > max_gap (0.35)
    out2 = EngineOut(
        engine="e2",
        noul={**{h: 0.01 for h in HAZARD_IDS}, "destructive": 0.90},
        category={"read_only": 1.0},
        reversibility=0.1,
        latency_ms=50.0,
    )
    f = fuse([out1, out2])
    d = decide(f, "none", 0, False, "grant", pol)
    assert d.action == "escalate"
    assert any("engines disagree" in r for r in d.reasons)
