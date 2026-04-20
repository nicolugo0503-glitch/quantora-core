/**
 * QNT30641 Strategy Approval
 */
import { evaluateStrategyReadiness } from "./strategy_onboarding.js";

export function approveStrategy(store, strategyId) {
  store.registry = store.registry || [];
  const item = store.registry.find(x => x.strategy_id === strategyId);
  if (!item) return { ok: false, error: "strategy_not_found" };
  const readiness = evaluateStrategyReadiness(item);
  if (!readiness.ready) {
    return { ok: false, error: "strategy_not_ready", readiness };
  }
  item.approval_status = "approved";
  item.updated_at = new Date().toISOString();
  store.audit = store.audit || [];
  store.audit.push({
    event_id: `AUD_${Date.now()}`,
    strategy_id: strategyId,
    action: "approve_strategy",
    timestamp: item.updated_at
  });
  return { ok: true, strategy: item, readiness };
}
