export function generateExecutiveSummary(store, period){
  return {
    period: period || "UNSPECIFIED",
    capital_raised: Number(store.capital_raised || 0),
    capital_deployed: Number(store.capital_deployed || 0),
    active_products: Number(store.active_products || 0),
    active_clients: Number(store.active_clients || 0),
    risk_alerts: Number(store.risk_alerts || 0),
    overdue_obligations: Number(store.overdue_obligations || 0),
    generated_at: new Date().toISOString()
  };
}