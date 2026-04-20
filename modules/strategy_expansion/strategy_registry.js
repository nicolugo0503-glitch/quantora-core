/**
 * QNT30641 Strategy Registry
 * Institutional registry for internal and external strategies.
 */
export function registerStrategy(store, config) {
  const now = new Date().toISOString();
  const record = {
    strategy_id: config.strategy_id || `STRAT_${Date.now()}`,
    name: config.name || "Unnamed Strategy",
    manager_type: config.manager_type || "internal",
    manager_name: config.manager_name || "Quantora",
    asset_class: config.asset_class || "multi-asset",
    risk_band: config.risk_band || "medium",
    vehicle_ids: Array.isArray(config.vehicle_ids) ? config.vehicle_ids : [],
    execution_ready: Boolean(config.execution_ready),
    reporting_ready: Boolean(config.reporting_ready),
    compliance_ready: Boolean(config.compliance_ready),
    approval_status: config.approval_status || "pending",
    created_at: now,
    updated_at: now
  };
  store.registry = store.registry || [];
  store.registry.push(record);
  return record;
}

export function listStrategies(store) {
  return (store.registry || []).slice();
}
