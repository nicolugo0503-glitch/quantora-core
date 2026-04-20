# QNT30485 - Investor Ledger
# Isolated mission module. No core files modified.

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Investor:
    investor_id: str
    name: str
    status: str = "active"
    created_at: str = datetime.utcnow().isoformat()


@dataclass
class LedgerEntry:
    entry_id: str
    investor_id: str
    fund_id: str
    entry_type: str   # deposit | withdrawal | adjustment
    amount: float
    currency: str = "USD"
    note: str = ""
    created_at: str = datetime.utcnow().isoformat()


class InvestorLedger:
    def __init__(self):
        self.investors: Dict[str, Investor] = {}
        self.entries: List[LedgerEntry] = []

    def add_investor(self, investor_id: str, name: str, status: str = "active") -> Investor:
        investor = Investor(investor_id=investor_id, name=name, status=status)
        self.investors[investor_id] = investor
        return investor

    def record_entry(
        self,
        entry_id: str,
        investor_id: str,
        fund_id: str,
        entry_type: str,
        amount: float,
        currency: str = "USD",
        note: str = ""
    ) -> LedgerEntry:
        if investor_id not in self.investors:
            raise ValueError(f"Unknown investor_id: {investor_id}")
        if entry_type not in {"deposit", "withdrawal", "adjustment"}:
            raise ValueError("entry_type must be deposit, withdrawal, or adjustment")
        entry = LedgerEntry(
            entry_id=entry_id,
            investor_id=investor_id,
            fund_id=fund_id,
            entry_type=entry_type,
            amount=float(amount),
            currency=currency,
            note=note,
        )
        self.entries.append(entry)
        return entry

    def get_investor_entries(self, investor_id: str) -> List[Dict]:
        return [asdict(e) for e in self.entries if e.investor_id == investor_id]

    def get_fund_entries(self, fund_id: str) -> List[Dict]:
        return [asdict(e) for e in self.entries if e.fund_id == fund_id]

    def get_investor_net_contribution(self, investor_id: str, fund_id: Optional[str] = None) -> float:
        total = 0.0
        for e in self.entries:
            if e.investor_id != investor_id:
                continue
            if fund_id is not None and e.fund_id != fund_id:
                continue
            if e.entry_type == "deposit":
                total += e.amount
            elif e.entry_type == "withdrawal":
                total -= e.amount
            elif e.entry_type == "adjustment":
                total += e.amount
        return round(total, 2)

    def get_fund_cap_table(self, fund_id: str) -> List[Dict]:
        contributions: Dict[str, float] = {}
        for investor_id in self.investors.keys():
            net = self.get_investor_net_contribution(investor_id, fund_id=fund_id)
            if net != 0:
                contributions[investor_id] = net

        fund_total = sum(contributions.values())
        rows = []
        for investor_id, net in contributions.items():
            ownership_pct = 0.0 if fund_total == 0 else (net / fund_total) * 100.0
            rows.append({
                "investor_id": investor_id,
                "investor_name": self.investors[investor_id].name,
                "net_contribution": round(net, 2),
                "ownership_pct": round(ownership_pct, 4),
                "fund_id": fund_id,
            })
        rows.sort(key=lambda x: x["net_contribution"], reverse=True)
        return rows


if __name__ == "__main__":
    ledger = InvestorLedger()
    ledger.add_investor("INV001", "Nicolas Capital")
    ledger.add_investor("INV002", "Atlas Family Office")
    ledger.record_entry("LE001", "INV001", "FUND1", "deposit", 250000, note="Initial subscription")
    ledger.record_entry("LE002", "INV002", "FUND1", "deposit", 150000, note="Initial subscription")
    ledger.record_entry("LE003", "INV001", "FUND1", "withdrawal", 25000, note="Partial redemption")
    print(ledger.get_fund_cap_table("FUND1"))
