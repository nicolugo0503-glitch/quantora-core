export function registerChannel(store, config){
  const row = {
    channel_id: config.channel_id || `CHAN_${Date.now()}`,
    name: config.name || "Unnamed Channel",
    type: config.type || "direct_lp",
    allowed_products: Array.isArray(config.allowed_products) ? config.allowed_products : [],
    jurisdiction_rules: config.jurisdiction_rules || "global",
    investor_tier_rules: config.investor_tier_rules || "qualified",
    status: config.status || "active",
    created_at: new Date().toISOString()
  };
  store.channels = store.channels || [];
  store.channels.push(row);
  return row;
}

export function listChannels(store){
  return (store.channels || []).slice();
}