# QNT30487 - Investor Dashboard
# Additive mission module only. No core files modified.

from dataclasses import dataclass, asdict
from typing import Dict, List


@dataclass
class InvestorDashboardRow:
    investor_id: str
    investor_name: str
    fund_id: str
    shares_owned: float
    nav_per_share: float
    ownership_pct: float
    market_value: float
    net_contributions: float
    unrealized_gain: float


class InvestorDashboardEngine:
    def __init__(self):
        self.investors: Dict[str, dict] = {}
        self.ledger_rows: List[dict] = []
        self.nav_snapshots: Dict[str, dict] = {}

    def load_investors(self, investors: List[dict]) -> None:
        for inv in investors:
            self.investors[inv["investor_id"]] = inv

    def load_ledger(self, ledger_rows: List[dict]) -> None:
        self.ledger_rows = list(ledger_rows)

    def load_nav_snapshots(self, nav_snapshots: List[dict]) -> None:
        self.nav_snapshots = {row["fund_id"]: row for row in nav_snapshots}

    def _group_positions(self) -> Dict[str, Dict[str, float]]:
        grouped: Dict[str, Dict[str, float]] = {}
        for row in self.ledger_rows:
            investor_id = row["investor_id"]
            fund_id = row["fund_id"]
            shares_delta = float(row.get("shares_delta", 0.0))
            cash_delta = float(row.get("cash_delta", 0.0))
            grouped.setdefault(investor_id, {})
            grouped[investor_id].setdefault(fund_id + "__shares", 0.0)
            grouped[investor_id].setdefault(fund_id + "__cash", 0.0)
            grouped[investor_id][fund_id + "__shares"] += shares_delta
            grouped[investor_id][fund_id + "__cash"] += cash_delta
        return grouped

    def build_dashboard_rows(self) -> List[dict]:
        grouped = self._group_positions()
        rows: List[InvestorDashboardRow] = []

        for investor_id, fund_state in grouped.items():
            investor = self.investors.get(investor_id, {"investor_name": investor_id})
            for key, shares_owned in fund_state.items():
                if not key.endswith("__shares"):
                    continue

                fund_id = key.replace("__shares", "")
                nav = self.nav_snapshots.get(fund_id, {})
                total_shares = float(nav.get("total_shares", 0.0))
                nav_per_share = float(nav.get("nav_per_share", 0.0))
                market_value = shares_owned * nav_per_share
                net_contributions = -float(fund_state.get(fund_id + "__cash", 0.0))
                ownership_pct = (shares_owned / total_shares * 100.0) if total_shares else 0.0
                unrealized_gain = market_value - net_contributions

                rows.append(
                    InvestorDashboardRow(
                        investor_id=investor_id,
                        investor_name=investor.get("investor_name", investor_id),
                        fund_id=fund_id,
                        shares_owned=round(shares_owned, 6),
                        nav_per_share=round(nav_per_share, 6),
                        ownership_pct=round(ownership_pct, 6),
                        market_value=round(market_value, 2),
                        net_contributions=round(net_contributions, 2),
                        unrealized_gain=round(unrealized_gain, 2),
                    )
                )

        return [asdict(r) for r in rows]

    def build_investor_statement(self, investor_id: str) -> dict:
        rows = [r for r in self.build_dashboard_rows() if r["investor_id"] == investor_id]
        total_market_value = round(sum(r["market_value"] for r in rows), 2)
        total_net_contributions = round(sum(r["net_contributions"] for r in rows), 2)
        total_unrealized_gain = round(sum(r["unrealized_gain"] for r in rows), 2)

        return {
            "investor_id": investor_id,
            "investor_name": self.investors.get(investor_id, {}).get("investor_name", investor_id),
            "positions": rows,
            "totals": {
                "market_value": total_market_value,
                "net_contributions": total_net_contributions,
                "unrealized_gain": total_unrealized_gain,
            },
        }
