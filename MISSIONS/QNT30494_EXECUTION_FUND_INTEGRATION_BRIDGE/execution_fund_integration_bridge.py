# QNT30494 — EXECUTION ↔ FUND INTEGRATION BRIDGE
# Additive mission module only. No core files modified.
#
# Purpose:
# Upgrade an existing broker/execution layer (Alpaca-ready) into a fund-aware
# capital system adapter without rebuilding the broker connector itself.

from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional


@dataclass
class ExecutionContext:
    fund_id: str
    sleeve_id: str
    strategy_id: str
    symbol: str


class ExecutionFundIntegrationBridge:
    def __init__(self):
        self.symbol_strategy_map: Dict[str, str] = {}
        self.strategy_sleeve_map: Dict[str, str] = {}
        self.sleeve_fund_map: Dict[str, str] = {}
        self.default_fund_id: str = "UNASSIGNED_FUND"

    # -------------------------
    # Mapping registry
    # -------------------------
    def set_default_fund(self, fund_id: str) -> None:
        self.default_fund_id = str(fund_id)

    def map_symbol_to_strategy(self, symbol: str, strategy_id: str) -> None:
        self.symbol_strategy_map[str(symbol)] = str(strategy_id)

    def map_strategy_to_sleeve(self, strategy_id: str, sleeve_id: str) -> None:
        self.strategy_sleeve_map[str(strategy_id)] = str(sleeve_id)

    def map_sleeve_to_fund(self, sleeve_id: str, fund_id: str) -> None:
        self.sleeve_fund_map[str(sleeve_id)] = str(fund_id)

    def load_mapping_bundle(self, payload: Dict[str, Any]) -> None:
        self.default_fund_id = str(payload.get("default_fund_id", self.default_fund_id))
        for symbol, strategy_id in payload.get("symbol_strategy_map", {}).items():
            self.map_symbol_to_strategy(symbol, strategy_id)
        for strategy_id, sleeve_id in payload.get("strategy_sleeve_map", {}).items():
            self.map_strategy_to_sleeve(strategy_id, sleeve_id)
        for sleeve_id, fund_id in payload.get("sleeve_fund_map", {}).items():
            self.map_sleeve_to_fund(sleeve_id, fund_id)

    # -------------------------
    # Context resolution
    # -------------------------
    def resolve_context(
        self,
        symbol: str,
        strategy_id: Optional[str] = None,
        sleeve_id: Optional[str] = None,
        fund_id: Optional[str] = None,
    ) -> ExecutionContext:
        resolved_strategy_id = str(
            strategy_id or self.symbol_strategy_map.get(symbol, "UNMAPPED_STRATEGY")
        )
        resolved_sleeve_id = str(
            sleeve_id or self.strategy_sleeve_map.get(resolved_strategy_id, "UNMAPPED_SLEEVE")
        )
        resolved_fund_id = str(
            fund_id or self.sleeve_fund_map.get(resolved_sleeve_id, self.default_fund_id)
        )

        return ExecutionContext(
            fund_id=resolved_fund_id,
            sleeve_id=resolved_sleeve_id,
            strategy_id=resolved_strategy_id,
            symbol=str(symbol),
        )

    # -------------------------
    # Order enrichment
    # -------------------------
    def enrich_order_payload(self, order_payload: Dict[str, Any]) -> Dict[str, Any]:
        symbol = str(order_payload.get("symbol", ""))
        context = self.resolve_context(
            symbol=symbol,
            strategy_id=order_payload.get("strategy_id"),
            sleeve_id=order_payload.get("sleeve_id"),
            fund_id=order_payload.get("fund_id"),
        )

        enriched = dict(order_payload)
        enriched["fund_id"] = context.fund_id
        enriched["sleeve_id"] = context.sleeve_id
        enriched["strategy_id"] = context.strategy_id
        enriched["symbol"] = context.symbol
        return enriched

    def enrich_order_batch(self, order_payloads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.enrich_order_payload(x) for x in order_payloads]

    # -------------------------
    # Position attribution
    # -------------------------
    def attribute_position_row(self, position_row: Dict[str, Any]) -> Dict[str, Any]:
        symbol = str(position_row.get("symbol", ""))
        context = self.resolve_context(
            symbol=symbol,
            strategy_id=position_row.get("strategy_id"),
            sleeve_id=position_row.get("sleeve_id"),
            fund_id=position_row.get("fund_id"),
        )

        attributed = dict(position_row)
        attributed["fund_id"] = context.fund_id
        attributed["sleeve_id"] = context.sleeve_id
        attributed["strategy_id"] = context.strategy_id
        return attributed

    def attribute_position_batch(self, position_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.attribute_position_row(x) for x in position_rows]

    # -------------------------
    # Fund-aware aggregation
    # -------------------------
    def build_fund_position_book(self, position_rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        attributed = self.attribute_position_batch(position_rows)
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for row in attributed:
            grouped.setdefault(row["fund_id"], [])
            grouped[row["fund_id"]].append(row)
        return grouped

    def build_nav_inputs_by_fund(self, position_rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        grouped = self.build_fund_position_book(position_rows)
        nav_inputs: Dict[str, List[Dict[str, Any]]] = {}

        for fund_id, rows in grouped.items():
            nav_inputs[fund_id] = []
            for row in rows:
                nav_inputs[fund_id].append({
                    "strategy_id": row.get("strategy_id", "UNMAPPED_STRATEGY"),
                    "market_value": float(row.get("market_value", 0.0)),
                    "unrealized_pnl": float(row.get("unrealized_pnl", 0.0)),
                    "realized_pnl": float(row.get("realized_pnl", 0.0)),
                })
        return nav_inputs

    def summarize_exposure_by_fund(self, position_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped = self.build_fund_position_book(position_rows)
        output: List[Dict[str, Any]] = []
        for fund_id, rows in grouped.items():
            market_value = sum(float(x.get("market_value", 0.0)) for x in rows)
            unrealized_pnl = sum(float(x.get("unrealized_pnl", 0.0)) for x in rows)
            realized_pnl = sum(float(x.get("realized_pnl", 0.0)) for x in rows)
            output.append({
                "fund_id": fund_id,
                "position_count": len(rows),
                "market_value": round(market_value, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "realized_pnl": round(realized_pnl, 2),
                "total_pnl": round(unrealized_pnl + realized_pnl, 2),
            })
        return output

    # -------------------------
    # Downstream integration helpers
    # -------------------------
    def attach_execution_context_to_fills(self, fill_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        enriched = []
        for row in fill_rows:
            symbol = str(row.get("symbol", ""))
            context = self.resolve_context(
                symbol=symbol,
                strategy_id=row.get("strategy_id"),
                sleeve_id=row.get("sleeve_id"),
                fund_id=row.get("fund_id"),
            )
            fill_row = dict(row)
            fill_row["fund_id"] = context.fund_id
            fill_row["sleeve_id"] = context.sleeve_id
            fill_row["strategy_id"] = context.strategy_id
            enriched.append(fill_row)
        return enriched

    def build_execution_sync_packet(
        self,
        order_rows: List[Dict[str, Any]],
        position_rows: List[Dict[str, Any]],
        fill_rows: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        enriched_orders = self.enrich_order_batch(order_rows)
        attributed_positions = self.attribute_position_batch(position_rows)
        enriched_fills = self.attach_execution_context_to_fills(fill_rows or [])
        nav_inputs_by_fund = self.build_nav_inputs_by_fund(attributed_positions)
        exposure_summary = self.summarize_exposure_by_fund(attributed_positions)

        return {
            "orders": enriched_orders,
            "positions": attributed_positions,
            "fills": enriched_fills,
            "nav_inputs_by_fund": nav_inputs_by_fund,
            "exposure_summary": exposure_summary,
        }
