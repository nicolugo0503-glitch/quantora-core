export function assignProductToChannel(store, productId, channelId){
  store.mappings = store.mappings || [];
  const row = {
    mapping_id: `MAP_${Date.now()}`,
    product_id: productId,
    channel_id: channelId,
    assigned_at: new Date().toISOString(),
    status: "active"
  };
  store.mappings.push(row);
  return row;
}

export function routeInvestorViaChannel(store, investorId, productId, channelId){
  const mapping = (store.mappings || []).find(x => x.product_id === productId && x.channel_id === channelId && x.status === "active");
  return {
    investor_id: investorId,
    product_id: productId,
    channel_id: channelId,
    eligible: Boolean(mapping),
    route: Boolean(mapping) ? "channel -> intake -> onboarding -> ledger" : "blocked"
  };
}