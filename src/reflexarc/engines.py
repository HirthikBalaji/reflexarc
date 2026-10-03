from __future__ import annotations

import asyncio
import os
import threading
import time
from dataclasses import dataclass
from typing import Protocol

import httpx

from .questions import (
    CATEGORIES,
    CATEGORY_INSTRUCTIONS,
    HAZARDS,
    HAZARD_IDS,
    REVERSIBILITY_INSTRUCTIONS,
    REVERSIBILITY_LEVELS,
)


@dataclass
class EngineOut:
    engine: str
    noul: dict[str, float]        # hazard id -> P(true)
    category: dict[str, float]    # label -> probability
    reversibility: float          # expected level, 0..2
    latency_ms: float


class Engine(Protocol):
    name: str

    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def run(self, state: dict) -> EngineOut: ...


class LayaEngine:
    name = "laya"

    def __init__(self, checkpoint: str = "english") -> None:
        self.checkpoint = checkpoint
        self._lock = threading.Lock()
        self._router = None
        self._questions = self._build_questions()

    @staticmethod
    def _build_questions() -> dict:
        qs: dict = {}
        for q in HAZARDS:
            qs[q.id] = {
                "type": "noul",
                "instructions": q.instructions,
                "criteria": {"true": q.true_text, "false": q.false_text},
            }
        qs["reversibility"] = {
            "type": "score",
            "instructions": REVERSIBILITY_INSTRUCTIONS,
            "criteria": list(REVERSIBILITY_LEVELS),
        }
        qs["category"] = {
            "type": "choice",
            "instructions": CATEGORY_INSTRUCTIONS,
            "criteria": dict(CATEGORIES),
        }
        return qs

    async def start(self) -> None:
        from laya import Router
        self._router = Router()
        await asyncio.to_thread(self._router.preload, [self.checkpoint])

    async def stop(self) -> None:
        if self._router is not None and hasattr(self._router, "unload"):
            await asyncio.to_thread(self._router.unload)

    def _run_sync(self, state: dict) -> EngineOut:
        t0 = time.perf_counter()
        with self._lock:
            res = self._router.predict(state, self._questions, model=self.checkpoint)
        a = res["answers"]
        return EngineOut(
            engine=self.name,
            noul={h: float(a[h]["noul"]) for h in HAZARD_IDS},
            category={k: float(v) for k, v in a["category"]["probabilities"].items()},
            reversibility=float(a["reversibility"]["score"]),
            latency_ms=(time.perf_counter() - t0) * 1000,
        )

    async def run(self, state: dict) -> EngineOut:
        return await asyncio.to_thread(self._run_sync, state)


class OllamaEngine:
    """Local System 1 decision engine served via Ollama v0.35+ /v1/systemone."""
    name = "ollama"

    def __init__(
        self,
        model: str = "tev1:0.8b",
        endpoint: str = "http://localhost:11434/v1/systemone",
        timeout: float = 10.0,
    ) -> None:
        self.model = os.environ.get("REFLEXARC_OLLAMA_MODEL", model)
        self.endpoint = os.environ.get("REFLEXARC_OLLAMA_URL", endpoint)
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._questions = self._build_questions()

    @staticmethod
    def _build_questions() -> dict:
        qs: dict = {}
        for q in HAZARDS:
            qs[q.id] = {
                "type": "noul",
                "instructions": q.instructions,
                "criteria": {"true": q.true_text, "false": q.false_text},
            }
        qs["reversibility"] = {
            "type": "score",
            "instructions": REVERSIBILITY_INSTRUCTIONS,
            "criteria": list(REVERSIBILITY_LEVELS),
        }
        qs["category"] = {
            "type": "choice",
            "instructions": CATEGORY_INSTRUCTIONS,
            "criteria": dict(CATEGORIES),
        }
        return qs

    async def start(self) -> None:
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def stop(self) -> None:
        if self._client is not None:
            await self._client.aclose()

    async def run(self, state: dict) -> EngineOut:
        if self._client is None:
            raise RuntimeError("OllamaEngine not started. Call start() first.")

        # Serialize state dict to a clean representation for Ollama System One
        if isinstance(state, dict):
            state_text = f"tool: {state.get('tool', '')}\naction: {state.get('action', '')}"
        else:
            state_text = str(state)

        payload = {
            "model": self.model,
            "state": state_text,
            "questions": self._questions,
        }

        t0 = time.perf_counter()
        resp = await self._client.post(self.endpoint, json=payload)
        resp.raise_for_status()
        data = resp.json()
        a = data.get("answers", {})

        return EngineOut(
            engine=self.name,
            noul={h: float(a[h]["noul"]) for h in HAZARD_IDS},
            category={k: float(v) for k, v in a["category"]["probabilities"].items()},
            reversibility=float(a["reversibility"]["score"]),
            latency_ms=(time.perf_counter() - t0) * 1000,
        )


class JevEngine:
    name = "jev"

    def __init__(self, model: str = "jev-1.13") -> None:
        self.model = model
        self._cm = None
        self._client = None
        self._qs = None

    @staticmethod
    def _build_questions() -> dict:
        from typesafe_sdk import Choice, Noul, Score
        qs: dict = {q.id: Noul(instructions=q.instructions) for q in HAZARDS}
        qs["reversibility"] = Score(
            instructions=REVERSIBILITY_INSTRUCTIONS,
            criteria=list(REVERSIBILITY_LEVELS),
        )
        qs["category"] = Choice(instructions=CATEGORY_INSTRUCTIONS, criteria=dict(CATEGORIES))
        return qs

    async def start(self) -> None:
        from typesafe_sdk import AsyncTypeSafeClient
        self._cm = AsyncTypeSafeClient(model=self.model)
        self._client = await self._cm.__aenter__()
        self._qs = self._build_questions()

    async def stop(self) -> None:
        if self._cm is not None:
            await self._cm.__aexit__(None, None, None)

    async def run(self, state: dict) -> EngineOut:
        t0 = time.perf_counter()
        r = await self._client.system_one(state=state, questions=self._qs)
        return EngineOut(
            engine=self.name,
            noul={h: float(r.nouls[h].noul) for h in HAZARD_IDS},
            category={k: float(v) for k, v in r.choices["category"].probabilities.items()},
            reversibility=float(r.scores["reversibility"].score),
            latency_ms=(time.perf_counter() - t0) * 1000,
        )


def build_engines() -> list[Engine]:
    engines: list[Engine] = [LayaEngine()]

    # If Ollama is enabled or available locally (default), add as independent voter
    use_ollama = os.environ.get("REFLEXARC_USE_OLLAMA", "1") == "1"
    if use_ollama:
        engines.append(OllamaEngine())

    # If TypeSafe API key is configured and not local-only mode, add Jev
    if os.environ.get("TYPESAFE_API_KEY") and os.environ.get("REFLEXARC_LOCAL_ONLY") != "1":
        engines.append(JevEngine())

    return engines
