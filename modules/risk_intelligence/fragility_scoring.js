export function computeFragilityScore(entityId, context = {}) {
  const concentration = Number(context.concentration_score || 50);
  const volatility = Number(context.volatility_score || 50);
  const liquidity = Number(context.liquidity_score || 50);
  const reserveDependency = Number(context.reserve_dependency_score || 50);
  const score = Number(((concentration * 0.30) + (volatility * 0.25) + (liquidity * 0.25) + (reserveDependency * 0.20)).toFixed(2));
  return { entity_id: entityId, score, band: score >= 75 ? "high" : score >= 55 ? "elevated" : "controlled" };
}