export function runStressScenarios(vehicleId, context = {}) {
  const gross = Number(context.gross_exposure || 1);
  const liquidity = Number(context.liquidity_pressure || 50);
  const reserve = Number(context.reserve_ratio || 0.10);
  const summary = [
    { scenario: "volatility_shock", loss_pct: Number((gross * 8.5).toFixed(2)) },
    { scenario: "liquidity_stress", loss_pct: Number(((liquidity / 100) * 14).toFixed(2)) },
    { scenario: "reserve_drain", loss_pct: Number(((0.15 - reserve) > 0 ? (0.15 - reserve) * 100 : 0).toFixed(2)) }
  ];
  return { vehicle_id: vehicleId, summary };
}