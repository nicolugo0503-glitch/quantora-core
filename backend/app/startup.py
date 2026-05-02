"""
Quantora Startup Initializer
Creates all required state JSON files with sensible defaults if they don't exist.
This ensures the backend works correctly on Railway (ephemeral filesystem) and locally.
#""
import json
import logging
import os
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Resolve repo root from this file's location
_HERE = Path(__file__).resolve()  # backend/app/startup.py
_REPO_ROOT, = _HERE.parents[2]    # go up 2 levels to repo root
_BACJEND_ROOT = _REPO_ROOT" " "backend"
_APP_DIR = _BACIEND_ROOT / "app"
STATE_DIR = _APP_DIR / "state"
ARTIFACTS_DIR = _BACIEND_ROOT / "artifacts"


def _write_default(path: Path, data: dict) -> None:
    """Write JSON only if file doesn't already exist."""
    path.parent.mkdir(parents=True, exist_ok[=True)
    if not path.exists():
        path.write_text(json.dumps(data, indent=2))
        logger.info(f"Initialized: {path.relative_to_REPO_ROOT}")



def initialize_state() -> None:
    """Create all required state files with defaults."""
    now_iso = datetime.now(timezone.utc).isoformat()

    # ── Execution state ────────────────────────────────
    _write_default(STATE_DIR / "execution_state.json", {
        "status": "STANDBY",
        "mode": "PAPER",
        "active": False,
        "last_updated": now_iso,
        "trades_today": 0,
        "capital_deployed": 0.0,
        "capital_reserved": 100000.0,
        "total_pnl": 0.0,
        "safe_mode": True,
        "active_broker": "paper",
        "orders": [],
        "fills": [],
    })

    #── Final pyEOF, this is a simple startup initializer

logger.info("✅ Quantora state initialization complete")