/**
 * QNT30641 Allocation Universe Router
 */
export function buildAllocationUniverse(store, vehicleId) {
  const registry = store.registry || [];
  return registry.filter(
    x => x.approval_status === "approved" &&
         Array.isArray(x.vehicle_ids) &&
         x.vehicle_ids.includes(vehicleId)
  );
}

export function routeStrategyEligibility(store, vehicleId, strategyId) {
  const match = buildAllocationUniverse(store, vehicleId).find(x => x.strategy_id === strategyId);
  return {
    vehicle_id: vehicleId,
    strategy_id: strategyId,
    eligible: Boolean(match)
  };
}
