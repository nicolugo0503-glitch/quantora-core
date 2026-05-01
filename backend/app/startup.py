"""
Quantora Startup Initializer
Creates all required state JSON files with sensible defaults if they don't exist.
This ensures the backend works correctly on Railway (ephemeral filesystem) and locally.
"""
import json
import logging
import os
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Resolve repo root from this file's location
_HERE = Path(__file__).resolve()
# backend/app/startup.py → go up 2 levels to repo root
_REPO_ROOT = _HERE.parents[2]
_BACKEND_ROOT = _REPO_ROOT / "backend"
_APP_DIR = _BACKEND_ROOT / "app"
STATE_DIR = _APP_DIR / "state"
ARTIFACTS_DIR = _BACKEND_ROOT / "artifacts"


def _write_default(path: Path, data: dict) -> None:
    """Write JSON only if file doesn't already exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(data, indent=2))
        logger.info(f"Initialized: {path.relative_to(_REPO_ROOT)}")


def initialize_state() -> None:
    """Create all required state files with defaults."""
    now_iso = datetime.now(timezone.utc).isoformat()

    # ── Execution state ───────────────────────────────────────────────────────
    _write_default(STATE_DIR / "execution_state.json", {
        "status": "STANDBY",
        "mode": "PAPER",
        "active": False,
        "last_updated": now_iso,
        "trades_today": 0,
        "capital_deployed": 0.0,
        "capital_reserved": 100000.0,
        "total_pnl": 0.0,
    })

    _write_default(STATE_DIR / "risk_kill_switch_state.json", {
        "kill_switch_active": False,
        "reason": None,
        "max_drawdown_pct": 10.0,
        "current_drawdown_pct": 0.0,
        "last_triggered": None,
        "last_updated": now_iso,
    })

    _write_default(STATE_DIR / "strategy_deployment_state.json", {
        "active_strategies": [],
        "deployed_capital": {},
        "strategy_performance": {},
        "last_updated": now_iso,
    })

    _write_default(STATE_DIR / "performance_engine_state.json", {
        "total_return_pct": 0.0,
        "sharpe_ratio": 0.0,
        "max_drawdown_pct": 0.0,
        "win_rate": 0.0,
        "avg_trade_pct": 0.0,
        "trades_total": 0,
        "last_updated": now_iso,
    })

    _write_default(STATE_DIR / "autonomous_execution_state.json", {
        "autonomous_mode": False,
        "confidence_threshold": 0.75,
        "max_position_size": 0.05,
        "current_positions": [],
        "last_updated": now_iso,
    })

    _write_default(STATE_DIR / "live_broker_truth_state.json", {
        "broker_connected": False,
        "broker_name": "Paper Trading",
        "account_id": "PAPER-001",
        "buying_power": 100000.0,
        "portfolio_value": 100000.0,
        "last_sync": now_iso,
        "positions": [],
    })

    _write_default(STATE_DIR / "real_position_fill_broker_sync_state.json", {
        "sync_status": "IDLE",
        "last_sync": now_iso,
        "open_positions": [],
        "pending_fills": [],
    })

    _write_default(STATE_DIR / "real_pnl_equity_exposure_truth_state.json", {
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "total_equity": 100000.0,
        "gross_exposure": 0.0,
        "net_exposure": 0.0,
        "beta": 0.0,
        "last_updated": now_iso,
    })

    _write_default(STATE_DIR / "real_order_entry_surface_state.json", {
        "orders_today": [],
        "pending_orders": [],
        "last_updated": now_iso,
    })

    _write_default(STATE_DIR / "live_broker_credential_vault_state.json", {
        "broker": "paper",
        "api_key_configured": False,
        "paper_trading": True,
        "last_updated": now_iso,
    })

    _write_default(STATE_DIR / "broker_session_handshake_state.json", {
        "session_active": False,
        "broker": "paper",
        "latency_ms": 0,
        "last_handshake": None,
        "last_updated": now_iso,
    })

    _write_default(STATE_DIR / "position_reconciliation_state.json", {
        "reconciled": True,
        "discrepancies": [],
        "last_reconcile": now_iso,
    })

    _write_default(STATE_DIR / "broker_cash_margin_state.json", {
        "cash_available": 100000.0,
        "margin_available": 0.0,
        "buying_power": 100000.0,
        "margin_used": 0.0,
        "last_updated": now_iso,
    })

    # ── Artifacts ─────────────────────────────────────────────────────────────
    _write_default(ARTIFACTS_DIR / "capital_ledger.json", {
        "total_capital": 100000.0,
        "deployed_capital": 0.0,
        "cash_reserve": 100000.0,
        "transactions": [],
        "last_updated": now_iso,
    })

    _write_default(ARTIFACTS_DIR / "trade_history.json", {
        "trades": [],
        "last_updated": now_iso,
    })

    # ── Auth / users ──────────────────────────────────────────────────────────
    auth_db = _APP_DIR / "auth_db.json"
    if not auth_db.exists():
        auth_db.write_text(json.dumps({
            "users": [{
                "id": "admin-001",
                "username": "admin",
                "email": "admin@quantora.ai",
                "hashed_password": "$2b$12$placeholder_hash_change_in_production",
                "role": "admin",
                "created": now_iso,
            }]
        }, indent=2))

    logger.info("✅ Quantora state initialization complete")
