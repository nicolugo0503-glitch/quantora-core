
# QNT30516 — Fee Engine (Management + Performance Fees)

from datetime import datetime, timezone

def _ts():
    return datetime.now(timezone.utc).isoformat()

class QNT30516FeeEngine:
    def __init__(self, mgmt_fee_pct=2.0, perf_fee_pct=20.0):
        self.mgmt_fee_pct = mgmt_fee_pct
        self.perf_fee_pct = perf_fee_pct
        self.ledger = []

    def calculate_fees(self, fund_id, nav, pnl):
        mgmt_fee = nav * (self.mgmt_fee_pct / 100)
        perf_fee = max(pnl, 0) * (self.perf_fee_pct / 100)

        row = {
            "timestamp": _ts(),
            "fund_id": fund_id,
            "nav": nav,
            "pnl": pnl,
            "management_fee": round(mgmt_fee, 2),
            "performance_fee": round(perf_fee, 2),
            "total_fee": round(mgmt_fee + perf_fee, 2)
        }

        self.ledger.append(row)
        return row

    def get_ledger(self):
        return self.ledger[-200:]
