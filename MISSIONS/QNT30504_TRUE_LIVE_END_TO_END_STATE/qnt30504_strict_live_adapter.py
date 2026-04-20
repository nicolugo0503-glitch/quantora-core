# QNT30504 — Strict live adapter wrapper
# Additive mission module only. No existing core files modified.
#
# PURPOSE
# Enforce a true-live policy so the backend can refuse to serve demo fallback state.

from typing import Any, Dict


class QNT30504StrictLiveAdapter:
    def __init__(self, base_adapter: Any, require_live_data: bool = True) -> None:
        self.base_adapter = base_adapter
        self.require_live_data = bool(require_live_data)

    def _ensure_live(self, payload: Dict[str, Any], payload_name: str) -> Dict[str, Any]:
        if not self.require_live_data:
            return payload

        if payload_name == "runtime":
            status = str(payload.get("status", "")).lower()
            if not payload or "fallback" in status or "missing" in status or status in ("unknown", ""):
                return {
                    "status": "live-data-required",
                    "cycle_count": 0,
                    "nav": 0.0,
                    "active_fund": "",
                    "pnl": 0.0,
                    "last_updated": payload.get("last_updated", ""),
                    "error": "strict live mode enabled: runtime fallback rejected",
                }
            return payload

        if payload_name in ("funds", "investors"):
            rows = payload.get("sleeves") if payload_name == "funds" else payload.get("rows")
            if not rows:
                key = "sleeves" if payload_name == "funds" else "rows"
                return {
                    key: [],
                    "last_updated": payload.get("last_updated", ""),
                    "error": f"strict live mode enabled: {payload_name} fallback rejected",
                }
            return payload

        if payload_name == "exposure":
            source = str(payload.get("source", "")).lower()
            if not payload or "fallback" in source:
                return {
                    "pnl": 0.0,
                    "market_value": 0.0,
                    "source": "strict-live-rejected-fallback",
                    "last_updated": payload.get("last_updated", ""),
                    "error": "strict live mode enabled: exposure fallback rejected",
                }
            return payload

        return payload

    def get_runtime_state(self) -> Dict[str, Any]:
        return self._ensure_live(self.base_adapter.get_runtime_state(), "runtime")

    def get_fund_summary(self) -> Dict[str, Any]:
        return self._ensure_live(self.base_adapter.get_fund_summary(), "funds")

    def get_investor_overview(self) -> Dict[str, Any]:
        return self._ensure_live(self.base_adapter.get_investor_overview(), "investors")

    def get_exposure_summary(self) -> Dict[str, Any]:
        return self._ensure_live(self.base_adapter.get_exposure_summary(), "exposure")

    def apply_action(self, action: str) -> Dict[str, Any]:
        return self.base_adapter.apply_action(action)
