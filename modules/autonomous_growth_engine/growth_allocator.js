export function buildGrowthBudget(plan = {}) {
  const deployable = Number(plan.deployable_capital || 0);
  const confidence = Number(plan.confidence_score || 0);
  const budget = deployable * Math.min(Math.max(confidence / 140, 0.18), 0.55);
  return {
    growth_budget: Number(budget.toFixed(2)),
    product_launch_budget: Number((budget * 0.38).toFixed(2)),
    channel_activation_budget: Number((budget * 0.27).toFixed(2)),
    coverage_budget: Number((budget * 0.20).toFixed(2)),
    contingency_budget: Number((budget * 0.15).toFixed(2))
  };
}
