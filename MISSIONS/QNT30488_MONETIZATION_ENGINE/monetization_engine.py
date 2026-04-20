# QNT30488 - Monetization Engine
# Additive mission module only. No core files modified.

from dataclasses import dataclass, asdict
from typing import Dict, List


@dataclass
class FeeEvent:
    fund_id: str
    investor_id: str
    fee_type: str
    amount: float
    period: str


class MonetizationEngine:
    def __init__(self):
        self.subscription_plans: Dict[str, dict] = {}
        self.management_fee_rules: Dict[str, dict] = {}
        self.performance_fee_rules: Dict[str, dict] = {}

    def set_subscription_plan(self, plan_id: str, monthly_price: float, features: List[str]) -> None:
        self.subscription_plans[plan_id] = {
            "plan_id": plan_id,
            "monthly_price": float(monthly_price),
            "features": list(features),
        }

    def set_management_fee_rule(self, fund_id: str, annual_rate: float) -> None:
        self.management_fee_rules[fund_id] = {
            "fund_id": fund_id,
            "annual_rate": float(annual_rate),
        }

    def set_performance_fee_rule(self, fund_id: str, rate: float, hurdle_return: float = 0.0) -> None:
        self.performance_fee_rules[fund_id] = {
            "fund_id": fund_id,
            "rate": float(rate),
            "hurdle_return": float(hurdle_return),
        }

    def compute_monthly_subscription_revenue(self, active_accounts: List[dict]) -> dict:
        rows = []
        total = 0.0
        for acct in active_accounts:
            plan = self.subscription_plans.get(acct["plan_id"], {})
            amount = float(plan.get("monthly_price", 0.0))
            total += amount
            rows.append({
                "account_id": acct["account_id"],
                "plan_id": acct["plan_id"],
                "monthly_price": round(amount, 2),
            })
        return {
            "total_monthly_subscription_revenue": round(total, 2),
            "accounts": rows,
        }

    def compute_management_fee(self, fund_id: str, avg_aum: float, period_days: int = 30) -> float:
        rule = self.management_fee_rules.get(fund_id, {})
        annual_rate = float(rule.get("annual_rate", 0.0))
        return round(avg_aum * annual_rate * (period_days / 365.0), 2)

    def compute_performance_fee(self, fund_id: str, net_profit: float, starting_nav: float) -> float:
        rule = self.performance_fee_rules.get(fund_id, {})
        rate = float(rule.get("rate", 0.0))
        hurdle_return = float(rule.get("hurdle_return", 0.0))
        hurdle_amount = starting_nav * hurdle_return
        billable_profit = max(0.0, net_profit - hurdle_amount)
        return round(billable_profit * rate, 2)

    def build_fee_events(
        self,
        fund_id: str,
        investor_allocations: List[dict],
        management_fee_total: float,
        performance_fee_total: float,
        period: str,
    ) -> List[dict]:
        total_market_value = sum(float(x.get("market_value", 0.0)) for x in investor_allocations) or 1.0
        rows: List[FeeEvent] = []

        for alloc in investor_allocations:
            investor_id = alloc["investor_id"]
            market_value = float(alloc.get("market_value", 0.0))
            share = market_value / total_market_value

            if management_fee_total > 0:
                rows.append(FeeEvent(
                    fund_id=fund_id,
                    investor_id=investor_id,
                    fee_type="management_fee",
                    amount=round(management_fee_total * share, 2),
                    period=period,
                ))

            if performance_fee_total > 0:
                rows.append(FeeEvent(
                    fund_id=fund_id,
                    investor_id=investor_id,
                    fee_type="performance_fee",
                    amount=round(performance_fee_total * share, 2),
                    period=period,
                ))

        return [asdict(r) for r in rows]
