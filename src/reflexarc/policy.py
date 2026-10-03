from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .fusion import Fused
from .questions import HAZARD_IDS

Authority = Literal["shadow", "restrict", "grant"]
RuleHit = Literal["deny", "allowlisted", "none"]


@dataclass(frozen=True)
class Policy:
    # Initial thresholds. Calibrated later via empirical calibration.
    allow_max: dict[str, float] = field(default_factory=lambda: {h: 0.05 for h in HAZARD_IDS})
    deny_min: float = 0.90        # every engine at or above this => deny
    max_gap: float = 0.35         # per-hazard engine disagreement tolerated
    max_cat_jsd: float = 0.30
    max_reversibility: float = 1.2
    version: str = "v0-initial"


@dataclass
class Decision:
    action: Literal["allow", "deny", "escalate"]
    reasons: list[str]


def decide(
    f: Fused | None,
    rule: RuleHit,
    novelty: int,
    truncated: bool,
    authority: Authority,
    pol: Policy,
) -> Decision:
    if rule == "deny":
        return Decision("deny", ["rule: deny-list"])
    if f is None:
        return Decision("escalate", ["no engine output"])

    # Both engines clearly flag a hazard -> deny (needs at least restrict authority)
    if authority != "shadow":
        for h in HAZARD_IDS:
            if f.p_min[h] >= pol.deny_min:
                return Decision("deny", [f"both engines flag {h} (min p={f.p_min[h]:.2f})"])

    reasons: list[str] = []
    for h in HAZARD_IDS:
        if f.p[h] > pol.allow_max[h]:
            reasons.append(f"{h}: p={f.p[h]:.2f} above allow limit {pol.allow_max[h]:.2f}")
        if f.gap[h] > pol.max_gap:
            reasons.append(f"{h}: engines disagree (gap {f.gap[h]:.2f})")
    if f.cat_jsd > pol.max_cat_jsd:
        reasons.append(f"category: engines disagree (JSD {f.cat_jsd:.2f})")
    if f.reversibility > pol.max_reversibility:
        reasons.append(f"reversibility level {f.reversibility:.2f} too high")
    if truncated:
        reasons.append("input was clipped; System 1 saw only part of it")
    if novelty > 0:
        reasons.append(f"{novelty} target(s) not mentioned in the user's goal")
    if f.n_engines < 2:
        reasons.append("only one engine answered; no disagreement signal")

    if reasons:
        return Decision("escalate", reasons)
    if rule == "allowlisted" or authority == "grant":
        return Decision("allow", ["reflex clear"])
    return Decision("escalate", ["not allow-listed and System 1 has not earned grant authority"])
