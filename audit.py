"""
audit.py — Append-only Audit Trail
Logs every detection run with metrics, ring summaries, and LLM verdicts.

Fixes applied:
  - AUDIT_FILE resolved relative to this file, not CWD
  - Atomic write via temp file + os.replace() — no corrupt JSON on crash
  - Bare except replaced with explicit json.JSONDecodeError + logging
  - Thread-safe write using threading.Lock
"""

import json
import logging
import os
import tempfile
import threading
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_HERE = Path(__file__).parent
LOGS_DIR = _HERE / "logs"
AUDIT_FILE = LOGS_DIR / "audit_log.json"

_write_lock = threading.Lock()


def load_log() -> list:
    """Load the audit log. Returns [] if missing or corrupt."""
    if not AUDIT_FILE.exists():
        return []
    try:
        with open(AUDIT_FILE, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        logger.error("audit_log.json is corrupt: %s — returning empty log", exc)
        return []


def save_log(log: list) -> None:
    """
    Atomically write the log to disk.
    Writes to a temp file first, then os.replace() — crash-safe.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=LOGS_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, AUDIT_FILE)
    except Exception:
        os.unlink(tmp_path)
        raise


def log_detection(rings: list, metrics: dict, source: str = "auto") -> dict:
    """Append a new detection entry and return it."""
    with _write_lock:
        log = load_log()
        entry = {
            "run_id": f"RUN_{len(log) + 1:04d}",
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "rings_detected": len(rings),
            "metrics": metrics,
            "ring_summary": [
                {
                    "cluster_id": r["cluster_id"],
                    "confidence_score": r["confidence_score"],
                    "member_count": r["member_count"],
                    "merchant_count": r["merchant_count"],
                    "damage_inr": r["total_damage_inr"],
                    "precision": r["precision"],
                    "signals_used": list(r["signals"].keys()),
                    "llm_verdict": r.get("llm_verdict", "pending"),
                }
                for r in rings
            ],
        }
        log.append(entry)
        save_log(log)
    return entry


def get_log() -> list:
    """Public read accessor."""
    return load_log()
