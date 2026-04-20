# QNT30486 - Fund NAV Engine
# Additive mission module only. No core files modified.

from dataclasses import dataclass, asdict
from typing import Dict, List


@dataclass
class PositionSnapshot:
    strategy_id: str
    market_value: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0


@dataclass
class FundNAVSnapshot:
    fund_id: str
    gross_assets: float
    liabilities: float
    net_assets: float
    nav: float
    nav_per_share: float
    total_shares: float


class FundNAVEngine:
    def __init__(self):
        self.cash_balances: Dict[str, float] = {}
        self.liabilities: Dict[str, float] = {}
        self.position_books: Dict[str, List[PositionSnapshot]] = {}
        self.share_registry: Dict[str, float] = {}

    def set_cash(self, fund_id: str, amount: float) -> None:
        self.cash_balances[fund_id] = float(amount)

    def set_liabilities(self, fund_id: str, amount: float) -> None:
        self.liabilities[fund_id] = float(amount)

    def set_total_shares(self, fund_id: str, shares: float) -> None:
        self.share_registry[fund_id] = float(shares)

    def load_positions(self, fund_id: str, positions: List[dict]) -> None:
        self.position_books[fund_id] = [
            PositionSnapshot(**p) if not isinstance(p, PositionSnapshot) else p
            for p in positions
        ]

    def get_market_value(self, fund_id: str) -> float:
        return sum(p.market_value for p in self.position_books.get(fund_id, []))

    def get_total_pnl(self, fund_id: str) -> float:
        return sum(
            p.unrealized_pnl + p.realized_pnl
            for p in self.position_books.get(fund_id, [])
        )

    def calculate_nav(self, fund_id: str) -> FundNAVSnapshot:
        cash = self.cash_balances.get(fund_id, 0.0)
        liabilities = self.liabilities.get(fund_id, 0.0)
        market_value = self.get_market_value(fund_id)
        gross_assets = cash + market_value
        net_assets = gross_assets - liabilities
        shares = self.share_registry.get(fund_id, 1.0)
        nav_per_share = net_assets / shares if shares else 0.0

        return FundNAVSnapshot(
            fund_id=fund_id,
            gross_assets=round(gross_assets, 2),
            liabilities=round(liabilities, 2),
            net_assets=round(net_assets, 2),
            nav=round(net_assets, 2),
            nav_per_share=round(nav_per_share, 6),
            total_shares=round(shares, 6),
        )

    def snapshot_dict(self, fund_id: str) -> dict:
        return asdict(self.calculate_nav(fund_id))
