export function registerClient(store, config){
  const row = {
    client_id: config.client_id || `CLIENT_${Date.now()}`,
    name: config.name || "Unnamed Client",
    channel_origin: config.channel_origin || "direct",
    relationship_status: config.relationship_status || "prospect",
    current_capital: Number(config.current_capital || 0),
    potential_capital: Number(config.potential_capital || 0),
    engagement_score: Number(config.engagement_score || 50),
    priority_tier: config.priority_tier || "standard",
    coverage_owner_id: config.coverage_owner_id || null,
    created_at: new Date().toISOString()
  };
  store.clients = store.clients || [];
  store.clients.push(row);
  return row;
}

export function listClients(store){
  return (store.clients || []).slice();
}