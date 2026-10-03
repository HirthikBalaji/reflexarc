# ReflexArc

**A System 1 "reflex layer" for AI agents, built on Laya, Ollama, and Jev.**

ReflexArc intercepts agent-proposed actions (shell commands, file writes, network calls) through a fast (~35 ms) reflex composed of **two independent System 1 decision models**. Their consensus and calibrated probabilities determine whether an action is **allowed**, **denied**, or **escalated** to a System 2 judge (Claude) and human review.

---

## Architecture Overview

```
Agent Proposed Action
         │
         ▼
[0 Normalize + Redact]    (NFKC, control stripping, secret redactor)
         │
         ▼
[1 Deterministic Rules]   (Hard deny-list & anchored allow-list)
         │
         ▼
[2 Multi-Engine Reflex]   Laya (local torch)  ‖  Ollama /v1/systemone (local)  ‖  Jev (hosted)
         │
         ▼
[3 Disagreement Fusion]   (Mean probabilities, JSD divergence, disagreement gap)
         │
         ▼
[4 Policy & Authority]    (Shadow → Restrict → Grant state machine)
         │
   ├── Allow
   ├── Deny
   └── Escalate ────────► [5 System 2: Claude Judge] ─► Allow / Deny / Needs Human
                                   │
                                   ▼
                       [6 SQLite Audit Ledger] ─► Calibration & Distillation Flywheel
```

---

## Quick Start

### 1. Requirements
* Python 3.12+ (Tested on Python 3.13)
* `uv` package manager
* Local Ollama (`v0.35.0+`) running with `tev1:0.8b` (already installed and active)

### 2. Run Tests
```powershell
uv run pytest
```
All 20 test cases cover:
* Question schemas & validation (`tests/test_questions.py`)
* Asynchronous parallel inference (`tests/test_engines.py`)
* Disagreement fusion & policy rules (`tests/test_policy.py`)
* FastAPI Gateway endpoints (`tests/test_gateway.py`)
* Claude Code fail-closed hooks (`tests/test_hooks.py`)
* Statistical calibration & earned authority (`tests/test_eval.py`)

### 3. Start the Gateway
```powershell
uv run uvicorn reflexarc.gateway:app --host 127.0.0.1 --port 8787
```

---

## Claude Code Integration

Configure `.claude/settings.json`:
```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python",
            "args": ["${CLAUDE_PROJECT_DIR}/integrations/claude_code/goal_hook.py"]
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash|Write|Edit|mcp__.*",
        "hooks": [
          {
            "type": "command",
            "command": "python",
            "args": ["${CLAUDE_PROJECT_DIR}/integrations/claude_code/pretool_hook.py"],
            "timeout": 20
          }
        ]
      }
    ]
  }
}
```

The hooks are strictly **fail-closed**: if the gateway is unreachable or crashes, `pretool_hook.py` exits with code `2` to block execution.
