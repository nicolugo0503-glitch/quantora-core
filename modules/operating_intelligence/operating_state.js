export function buildOperatingSnapshot(store, period){
  return {
    period: period || "UNSPECIFIED",
    capital_state: store.capital_state || "stable",
    risk_state: store.risk_state || "watch",
    reporting_state: store.reporting_state || "strong",
    product_state: store.product_state || "building",
    generated_at: new Date().toISOString()
  };
}