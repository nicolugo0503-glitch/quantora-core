# QNT30513 — Treasury + Cash Management Layer
# Additive mission module only. No existing core files modified.

from datetime import datetime, timezone
from typing import Dict, Any, List


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


class QNT30513TreasuryEngine:
    def __init__(self) -> None:
        self.cash_ledger: List[Dict[str, Any]] = []
        self.account_balances: Dict[str, float] = {}
        self.reserved_cash: Dict[str, float] = {}
        self.last_snapshot: Dict[str, Any] = {}

    def record_cash_event(
        self,
        fund_id: str,
        event_type: str,
        amount: float,
        note: str = "",
    ) -> Dict[str, Any]:
        amount = float(amount)
        self.account_balances.setdefault(fund_id, 0.0)

        if event_type in ("deposit", "credit", "release_reserved"):
            self.account_balances[fund_id] += amount
        elif event_type in ("withdrawal", "debit", "reserve_cash"):
            self.account_balances[fund_id] -= amount

        row = {
            "timestamp": _ts(),
            "fund_id": fund_id,
            "event_type": event_type,
            "amount": round(amount, 2),
            "note": note,
            "balance_after": round(self.account_balances[fund_id], 2),
        }
        self.cash_ledger.append(row)
        self.cash_ledger = self.cash_ledger[-1000:]
        return row

    def reserve_cash(self, fund_id: str, amount: float, note: str = "rebalance reserve") -> Dict[str, Any]:
        amount = float(amount)
        self.reserved_cash[fund_id] = round(self.reserved_cash.get(fund_id, 0.0) + amount, 2)
        self.record_cash_event(fund_id, "reserve_cash", amount, note)
        return {
            "fund_id": fund_id,
            "reserved_cash": self.reserved_cash[fund_id],
            "available_cash": round(self.account_balances.get(fund_id, 0.0), 2),
        }

    def release_reserved_cash(self, fund_id: str, amount: float, note: str = "release reserve") -> Dict[str, Any]:
        amount = float(amount)
        current = self.reserved_cash.get(fund_id, 0.0)
        released = min(current, amount)
        self.reserved_cash[fund_id] = round(current - released, 2)
        self.record_cash_event(fund_id, "release_reserved", released, note)
        return {
            "fund_id": fund_id,
            "released_cash": round(released, 2),
            "reserved_cash": self.reserved_cash[fund_id],
            "available_cash": round(self.account_balances.get(fund_id, 0.0), 2),
        }

    def get_cash_summary(self, fund_id: str = "") -> Dict[str, Any]:
        if fund_id:
            available = round(self.account_balances.get(fund_id, 0.0), 2)
            reserved = round(self.reserved_cash.get(fund_id, 0.0), 2)
            total = round(available + reserved, 2)
            summary = {
                "fund_id": fund_id,
                "available_cash": available,
                "reserved_cash": reserved,
                "total_cash": total,
            }
            self.last_snapshot = {"timestamp": _ts(), "summary": summary}
            return summary

        rows = []
        for fid in sorted(set(list(self.account_balances.keys()) + list(self.reserved_cash.keys()))):
            available = round(self.account_balances.get(fid, 0.0), 2)
            reserved = round(self.reserved_cash.get(fid, 0.0), 2)
            rows.append({
                "fund_id": fid,
                "available_cash": available,
                "reserved_cash": reserved,
                "total_cash": round(available + reserved, 2),
            })
        snapshot = {"timestamp": _ts(), "rows": rows}
        self.last_snapshot = snapshot
        return snapshot

    def get_cash_ledger(self, fund_id: str = "", limit: int = 200) -> List[Dict[str, Any]]:
        rows = self.cash_ledger
        if fund_id:
            rows = [r for r in rows if r.get("fund_id") == fund_id]
        return rows[-limit:]
