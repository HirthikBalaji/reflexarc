from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .engines import EngineOut
from .questions import CATEGORIES, HAZARD_IDS


def jsd(p: np.ndarray, q: np.ndarray) -> float:
    """Jensen-Shannon divergence in bits, range 0..1."""
    p_sum = p.sum()
    q_sum = q.sum()
    p = p / p_sum if p_sum > 0 else np.ones_like(p) / len(p)
    q = q / q_sum if q_sum > 0 else np.ones_like(q) / len(q)
    m = 0.5 * (p + q)

    def kl(a: np.ndarray, b: np.ndarray) -> float:
        mask = (a > 0) & (b > 0)
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))

    return float(0.5 * kl(p, m) + 0.5 * kl(q, m))


@dataclass
class Fused:
    p: dict[str, float]            # mean P(true) per hazard
    p_min: dict[str, float]        # lowest engine's P per hazard
    gap: dict[str, float]          # max - min P per hazard (disagreement)
    reversibility: float
    rev_gap: float                 # normalized 0..1
    category: str                  # argmax of mean distribution
    cat_jsd: float                 # 0 when only one engine
    n_engines: int


def fuse(outs: list[EngineOut]) -> Fused:
    labels = list(CATEGORIES)
    p: dict[str, float] = {}
    p_min: dict[str, float] = {}
    gap: dict[str, float] = {}

    for h in HAZARD_IDS:
        vals = [o.noul[h] for o in outs]
        p[h] = float(np.mean(vals))
        p_min[h] = float(min(vals))
        gap[h] = float(max(vals) - min(vals))

    revs = [o.reversibility for o in outs]
    dists = [np.array([o.category.get(k, 0.0) for k in labels]) for o in outs]

    # Normalize distributions
    norm_dists = []
    for d in dists:
        s = d.sum()
        norm_dists.append(d / s if s > 0 else np.ones_like(d) / len(d))

    mean_dist = np.mean(norm_dists, axis=0)
    cat_jsd = jsd(norm_dists[0], norm_dists[1]) if len(norm_dists) >= 2 else 0.0

    return Fused(
        p=p,
        p_min=p_min,
        gap=gap,
        reversibility=float(np.mean(revs)),
        rev_gap=float((max(revs) - min(revs)) / 2.0),
        category=labels[int(np.argmax(mean_dist))],
        cat_jsd=cat_jsd,
        n_engines=len(outs),
    )
