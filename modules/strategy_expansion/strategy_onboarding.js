/**
 * QNT30641 Strategy Onboarding
 */
export function evaluateStrategyReadiness(strategy) {
  const checks = {
    mandate_defined: Boolean(strategy.name),
    execution_ready: Boolean(strategy.execution_ready),
    reporting_ready: Boolean(strategy.reporting_ready),
    compliance_ready: Boolean(strategy.compliance_ready),
    vehicle_eligible: Array.isArray(strategy.vehicle_ids) && strategy.vehicle_ids.length > 0
  };
  const score = Object.values(checks).filter(Boolean).length;
  return {
    checks,
    readiness_score: score,
    ready: score === 5
  };
}
