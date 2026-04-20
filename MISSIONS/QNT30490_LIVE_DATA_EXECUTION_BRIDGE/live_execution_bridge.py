# QNT30490 — LIVE DATA + EXECUTION BRIDGE
# Additive mission module only. No core files modified.

from dataclasses import dataclass, asdict
from typing import List, Dict, Any


@dataclass
class BrokerPosition:
    symbol: str
    qty: float
    market_value: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    strategy_id: str = "UNMAPPED"


@dataclass
class BrokerOrder:
    order_id: str
    symbol: str
    side: str
    qty: float
    status: str
    filled_qty: float = 0.0
    avg_fill_price: float = 0.0
    strategy_id: str = "UNMAPPED"
    fund_id: str = "UNASSIGNED"


class LiveExecutionBridge:
    def __init__(self):
        self.position_mappings: Dict[str, str] = {}
        self.order_mappings: Dict[str, str] = {}
        self.last_sync: Dict[str, Any] = {}

    def map_symbol_to_strategy(self, symbol: str, strategy_id: str) -> None:
        self.position_mappings[symbol] = strategy_id

    def normalize_positions(self, broker_positions: List[dict]) -> List[dict]:
        normalized = []
        for row in broker_positions:
            symbol = row.get("symbol", "")
            normalized.append(asdict(BrokerPosition(
                symbol=symbol,
                qty=float(row.get("qty", 0.0)),
                market_value=float(row.get("market_value", 0.0)),
                unrealized_pnl=float(row.get("unrealized_pnl", 0.0)),
                realized_pnl=float(row.get("realized_pnl", 0.0)),
                strategy_id=self.position_mappings.get(symbol, row.get("strategy_id", "UNMAPPED")),
            )))
        return normalized

    def normalize_orders(self, broker_orders: List[dict], default_fund_id: str) -> List[dict]:
        normalized = []
        for row in broker_orders:
            symbol = row.get("symbol", "")
            normalized.append(asdict(BrokerOrder(
                order_id=str(row.get("order_id", "")),
                symbol=symbol,
                side=str(row.get("side", "")),
                qty=float(row.get("qty", 0.0)),
                status=str(row.get("status", "unknown")),
                filled_qty=float(row.get("filled_qty", 0.0)),
                avg_fill_price=float(row.get("avg_fill_price", 0.0)),
                strategy_id=self.position_mappings.get(symbol, row.get("strategy_id", "UNMAPPED")),
                fund_id=str(row.get("fund_id", default_fund_id)),
            )))
        return normalized

    def positions_to_nav_inputs(self, normalized_positions: List[dict]) -> List[dict]:
        nav_positions = []
        for row in normalized_positions:
            nav_positions.append({
                "strategy_id": row.get("strategy_id", "UNMAPPED"),
                "market_value": float(row.get("market_value", 0.0)),
                "unrealized_pnl": float(row.get("unrealized_pnl", 0.0)),
                "realized_pnl": float(row.get("realized_pnl", 0.0)),
            })
        return nav_positions

    def build_execution_snapshot(
        self,
        fund_id: str,
        broker_positions: List[dict],
        broker_orders: List[dict],
        cash: float,
        liabilities: float = 0.0,
        total_shares: float = 1.0,
    ) -> dict:
        normalized_positions = self.normalize_positions(broker_positions)
        normalized_orders = self.normalize_orders(broker_orders, default_fund_id=fund_id)
        nav_positions = self.positions_to_nav_inputs(normalized_positions)

        snapshot = {
            "fund_id": fund_id,
            "cash": float(cash),
            "liabilities": float(liabilities),
            "shares": float(total_shares),
            "positions": nav_positions,
            "open_orders": normalized_orders,
            "position_count": len(normalized_positions),
            "order_count": len(normalized_orders),
        }
        self.last_sync[fund_id] = snapshot
        return snapshot

    def sync_into_integration_cycle(
        self,
        integration_engine,
        fund_id: str,
        capital: float,
        broker_positions: List[dict],
        broker_orders: List[dict],
        cash: float,
        liabilities: float = 0.0,
        total_shares: float = 1.0,
        starting_nav: float = 0.0,
        net_profit: float = 0.0,
    ) -> dict:
        snapshot = self.build_execution_snapshot(
            fund_id=fund_id,
            broker_positions=broker_positions,
            broker_orders=broker_orders,
            cash=cash,
            liabilities=liabilities,
            total_shares=total_shares,
        )

        nav_inputs = {
            "cash": snapshot["cash"],
            "liabilities": snapshot["liabilities"],
            "shares": snapshot["shares"],
            "starting_nav": float(starting_nav),
            "net_profit": float(net_profit),
            "positions": snapshot["positions"],
        }

        result = integration_engine.run_full_cycle(
            fund_id=fund_id,
            capital=capital,
            nav_inputs=nav_inputs,
        )

        result["execution_snapshot"] = snapshot
        return result
