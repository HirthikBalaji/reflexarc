from __future__ import annotations

import asyncio
import os
import random
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from .engines import EngineOut, build_engines
from .fusion import fuse
from .judge import system2
from .ledger import Ledger
from .normalize import action_text, clip, targets
from .policy import Policy, decide
from .redact import redact
from .rules import classify

POLICY = Policy()
KEY = os.environ.get("REFLEXARC_KEY", "")
LOCAL_ONLY = os.environ.get("REFLEXARC_LOCAL_ONLY") == "1"
AUDIT_RATE = float(os.environ.get("REFLEXARC_AUDIT_RATE", "0.1"))
ENGINE_TIMEOUT = float(os.environ.get("REFLEXARC_ENGINE_TIMEOUT", "4.0"))

# Per-category authority; defaults to shadow
AUTHORITY: dict[str, str] = {}
GOALS: dict[str, str] = {}

app_state: dict[str, Any] = {}


def get_ledger() -> Ledger:
    if "ledger" not in app_state:
        app_state["ledger"] = Ledger()
    return app_state["ledger"]


def get_engines():
    if "engines" not in app_state:
        app_state["engines"] = build_engines()
    return app_state["engines"]


@asynccontextmanager
async def lifespan(_: FastAPI):
    engines = get_engines()
    await asyncio.gather(*(e.start() for e in engines))
    get_ledger()
    yield
    await asyncio.gather(*(e.stop() for e in engines))
    if "ledger" in app_state and hasattr(app_state["ledger"], "close"):
        app_state["ledger"].close()


app = FastAPI(title="ReflexArc Gateway", lifespan=lifespan)


class JudgeIn(BaseModel):
    tool: str
    input: dict[str, Any]
    session: str | None = None


class GoalIn(BaseModel):
    session: str
    goal: str


def _auth(authorization: str) -> None:
    if KEY and authorization != f"Bearer {KEY}":
        raise HTTPException(401, "bad key")


@app.post("/v1/session/goal")
async def set_goal(body: GoalIn, authorization: str = Header(default="")):
    _auth(authorization)
    GOALS[body.session] = redact(body.goal)[:1000]
    return {"ok": True}


@app.post("/v1/judge")
async def judge(req: JudgeIn, authorization: str = Header(default="")):
    _auth(authorization)
    t0 = time.perf_counter()
    engines = get_engines()

    text, truncated = clip(redact(action_text(req.tool, req.input)))
    goal = GOALS.get(req.session or "")
    rule = classify(text)
    novelty = len(targets(text) - targets(goal or ""))

    results = await asyncio.gather(
        *(
            asyncio.wait_for(
                e.run({"tool": req.tool, "action": text}),
                timeout=ENGINE_TIMEOUT,
            )
            for e in engines
        ),
        return_exceptions=True,
    )
    outs = [r for r in results if isinstance(r, EngineOut)]
    fused = fuse(outs) if outs else None

    category = fused.category if fused else "unknown"
    authority = AUTHORITY.get(category, "shadow")

    s1 = decide(fused, rule, novelty, truncated, authority, POLICY)
    final: str = s1.action
    judge_out: dict[str, Any] | None = None

    if s1.action == "escalate" and not LOCAL_ONLY:
        try:
            judge_out = await system2(req.tool, text, goal)
            final = {"allow": "allow", "deny": "deny"}.get(
                judge_out.get("verdict", ""), "ask"
            )
            # Claude cannot overrule a both-engines hard deny
            if s1.action == "deny":
                final = "deny"
        except Exception as exc:  # Fail closed on judge failure
            final = "ask"
            judge_out = {"error": repr(exc)}
    elif s1.action == "escalate":
        final = "ask"

    # Random audit of would-be allows
    if s1.action == "allow" and not LOCAL_ONLY and random.random() < AUDIT_RATE:
        asyncio.create_task(_audit(req.tool, text, goal, req.session))

    # Enforce rules immediately; otherwise enforce only once authority > shadow
    if rule == "deny":
        enforced = "deny"
    elif authority == "shadow":
        enforced = "none"
    else:
        enforced = final

    ledger = get_ledger()
    row_id = await ledger.write({
        "session": req.session,
        "tool": req.tool,
        "category": category,
        "action_redacted": text,
        "goal": goal,
        "engines": [o.__dict__ for o in outs],
        "fused": fused.__dict__ if fused else None,
        "s1_action": s1.action,
        "s1_reasons": s1.reasons,
        "authority": authority,
        "enforced": enforced,
        "judge": judge_out,
        "latency_ms": (time.perf_counter() - t0) * 1000,
        "policy_version": POLICY.version,
    })

    return {
        "id": row_id,
        "enforced": enforced,
        "would": final,
        "reason": "; ".join(
            s1.reasons + ([str(judge_out.get("reason", ""))] if judge_out else [])
        )[:600],
    }


async def _audit(tool: str, text: str, goal: str | None, session: str | None) -> None:
    try:
        j = await system2(tool, text, goal)
        ledger = get_ledger()
        await ledger.write({
            "session": session,
            "tool": tool,
            "action_redacted": text,
            "goal": goal,
            "s1_action": "allow",
            "audit_label": j,
            "policy_version": POLICY.version,
        })
    except Exception:
        pass
