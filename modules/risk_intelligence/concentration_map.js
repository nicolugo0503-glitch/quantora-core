export function buildConcentrationMap(vehicleId, context = {}) {
  const exposures = context.exposures || [];
  const total = exposures.reduce((s, x) => s + Math.max(0, Number(x.weight || 0)), 0) || 1;
  const normalized = exposures.map(x => ({
    key: x.key || x.strategy_id || x.asset_class || "UNKNOWN",
    weight: Number((Number(x.weight || 0) / total).toFixed(4))
  })).sort((a, b) => b.weight - a.weight);
  return {
    vehicle_id: vehicleId,
    total_weight: 1,
    top_key: normalized[0]?.key || null,
    top_weight: normalized[0]?.weight || 0,
    rows: normalized
  };
}