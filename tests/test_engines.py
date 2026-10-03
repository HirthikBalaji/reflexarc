import asyncio
import pytest
from reflexarc.engines import LayaEngine, OllamaEngine, EngineOut
from reflexarc.questions import HAZARD_IDS


@pytest.mark.asyncio
async def test_laya_engine():
    engine = LayaEngine(checkpoint="english")
    await engine.start()
    try:
        out = await engine.run({"tool": "Bash", "action": "ls -la /tmp"})
        assert isinstance(out, EngineOut)
        assert out.engine == "laya"
        assert len(out.noul) == len(HAZARD_IDS)
        assert 0.0 <= out.reversibility <= 2.0
        assert out.latency_ms > 0
    finally:
        await engine.stop()


@pytest.mark.asyncio
async def test_ollama_engine():
    engine = OllamaEngine(model="tev1:0.8b")
    await engine.start()
    try:
        out = await engine.run({"tool": "Bash", "action": "ls -la /tmp"})
        assert isinstance(out, EngineOut)
        assert out.engine == "ollama"
        assert len(out.noul) == len(HAZARD_IDS)
        assert 0.0 <= out.reversibility <= 2.0
        assert out.latency_ms > 0
    finally:
        await engine.stop()


@pytest.mark.asyncio
async def test_parallel_engines():
    laya = LayaEngine(checkpoint="english")
    ollama = OllamaEngine(model="tev1:0.8b")

    await asyncio.gather(laya.start(), ollama.start())
    try:
        state = {"tool": "Bash", "action": "rm -rf /"}
        results = await asyncio.gather(laya.run(state), ollama.run(state))
        assert len(results) == 2
        laya_out, ollama_out = results

        assert laya_out.engine == "laya"
        assert ollama_out.engine == "ollama"

        # Both should flag destructive
        assert laya_out.noul["destructive"] > 0.5
        assert ollama_out.noul["destructive"] > 0.5
    finally:
        await asyncio.gather(laya.stop(), ollama.stop())
