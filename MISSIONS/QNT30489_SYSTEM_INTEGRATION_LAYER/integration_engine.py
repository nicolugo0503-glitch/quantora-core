
# QNT30489 — SYSTEM INTEGRATION LAYER
# Orchestrates full capital lifecycle across modules (non-invasive)

from typing import Dict, Any

class QuantoraIntegrationEngine:

    def __init__(self, fund_engine, ledger_engine, nav_engine, dashboard_engine, monetization_engine):
        self.fund_engine = fund_engine
        self.ledger_engine = ledger_engine
        self.nav_engine = nav_engine
        self.dashboard_engine = dashboard_engine
        self.monetization_engine = monetization_engine

    def run_full_cycle(self, fund_id: str, capital: float, nav_inputs: Dict[str, Any]):
        # 1. Allocate capital → sleeves
        sleeve_allocations = self.fund_engine.allocate(fund_id, capital)

        # 2. Load NAV inputs
        self.nav_engine.set_cash(fund_id, nav_inputs.get("cash", 0))
        self.nav_engine.set_liabilities(fund_id, nav_inputs.get("liabilities", 0))
        self.nav_engine.set_total_shares(fund_id, nav_inputs.get("shares", 1))
        self.nav_engine.load_positions(fund_id, nav_inputs.get("positions", []))

        nav_snapshot = self.nav_engine.snapshot_dict(fund_id)

        # 3. Build investor dashboard
        self.dashboard_engine.load_nav_snapshots([nav_snapshot])
        dashboard_rows = self.dashboard_engine.build_dashboard_rows()

        # 4. Monetization
        mgmt_fee = self.monetization_engine.compute_management_fee(
            fund_id, nav_snapshot["nav"]
        )

        perf_fee = self.monetization_engine.compute_performance_fee(
            fund_id,
            net_profit=nav_inputs.get("net_profit", 0),
            starting_nav=nav_inputs.get("starting_nav", 0),
        )

        fee_events = self.monetization_engine.build_fee_events(
            fund_id,
            dashboard_rows,
            mgmt_fee,
            perf_fee,
            period="monthly"
        )

        return {
            "sleeve_allocations": sleeve_allocations,
            "nav_snapshot": nav_snapshot,
            "dashboard": dashboard_rows,
            "fees": fee_events
        }
