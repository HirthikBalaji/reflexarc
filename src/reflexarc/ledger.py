import asyncio
import json
import sqlite3
import time
import uuid
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions(
  id TEXT PRIMARY KEY,
  ts REAL,
  session TEXT,
  tool TEXT,
  category TEXT,
  action_redacted TEXT,
  goal TEXT,
  engines TEXT,
  fused TEXT,
  s1_action TEXT,
  s1_reasons TEXT,
  authority TEXT,
  enforced TEXT,
  judge TEXT,
  human_label TEXT,
  audit_label TEXT,
  latency_ms REAL,
  policy_version TEXT
);
CREATE INDEX IF NOT EXISTS idx_ts ON decisions(ts);
"""


class Ledger:
    """SQLite decision ledger for audit trails, distillation, and fine-tuning."""

    def __init__(self, path: str = "reflexarc.db") -> None:
        self.path = path
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript(_SCHEMA)

    def _insert(self, row: dict[str, Any]) -> str:
        row = {**row, "id": row.get("id") or uuid.uuid4().hex, "ts": time.time()}
        cols = ",".join(row.keys())
        qs = ",".join("?" for _ in row)
        vals = [
            json.dumps(v, default=str) if isinstance(v, (dict, list)) else v
            for v in row.values()
        ]
        self._db.execute(f"INSERT INTO decisions({cols}) VALUES({qs})", vals)
        self._db.commit()
        return str(row["id"])

    async def write(self, row: dict[str, Any]) -> str:
        return await asyncio.to_thread(self._insert, row)

    def _set(self, id_: str, col: str, value: Any) -> None:
        assert col in {"human_label", "audit_label", "judge"}
        serialized = json.dumps(value, default=str) if isinstance(value, (dict, list)) else str(value)
        self._db.execute(f"UPDATE decisions SET {col}=? WHERE id=?", (serialized, id_))
        self._db.commit()

    async def set(self, id_: str, col: str, value: Any) -> None:
        await asyncio.to_thread(self._set, id_, col, value)

    def close(self) -> None:
        self._db.close()
