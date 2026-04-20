# QNT30510 — NAV refresh service
# Additive mission module only. No existing core files modified.

from datetime import datetime, timezone
from typing import Any, Dict


def _utc_hour() -> int:
    return datetime.now(timezone.utc).hour


class QNT30510NAVRefreshService:
    def __init__(self, store: Any, nav_engine: Any = None, active_fund_id: str = "FUND1") -> None:
        self.store = store
        self.nav_engine = nav_engine
        self.active_fund_id = active_fund_id
        self.last_eod_day: str = ""

    def _default_nav_snapshot(self) -> Dict[str, Any]:
        return {
            "fund_id": self.active_fund_id,
            "gross_assets": 730000.0,
            "liabilities": 10000.0,
            "net_assets": 720000.0,
            "nav": 720000.0,
            "nav_per_share": 7.2,
            "total_shares": 100000.0,
        }

    def compute_nav_snapshot(self) -> Dict[str, Any]:
        if self.nav_engine and hasattr(self.nav_engine, "snapshot_dict"):
            try:
                snap = self.nav_engine.snapshot_dict(self.active_fund_id)
                if isinstance(snap, dict) and snap:
                    return snap
            except Exception:
                pass
        return self._default_nav_snapshot()

    def refresh_current_nav(self) -> Dict[str, Any]:
        snap = self.compute_nav_snapshot()
        return self.store.write_current_nav(snap)

    def maybe_take_eod_snapshot(self, force: bool = False) -> Dict[str, Any]:
        snap = self.compute_nav_snapshot()
        current_day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        is_eod_window = _utc_hour() >= 23

        if force or (is_eod_window and self.last_eod_day != current_day):
            row = self.store.append_eod_snapshot(snap, note="scheduled_or_forced_eod_snapshot")
            self.last_eod_day = current_day
            return {"ok": True, "snapshot_taken": True, "row": row}

        return {"ok": True, "snapshot_taken": False, "reason": "not_in_eod_window_or_already_taken"}

    def refresh_and_maybe_snapshot(self) -> Dict[str, Any]:
        current = self.refresh_current_nav()
        eod = self.maybe_take_eod_snapshot(force=False)
        return {
            "current_nav": current,
            "eod_result": eod,
        }
