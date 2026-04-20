export function buildOffering(config){
  return {
    product_id: config.product_id,
    minimum_commitment: Number(config.minimum_commitment || 10000),
    investor_tier: config.investor_tier || "qualified",
    liquidity_terms: config.liquidity_terms || "monthly",
    fee_schedule: config.fee_schedule || "2 and 20",
    distribution_policy: config.distribution_policy || "reinvest"
  };
}