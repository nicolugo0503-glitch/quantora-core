export function logClientInteraction(store, clientId, event){
  const row = {
    interaction_id: event.interaction_id || `INT_${Date.now()}`,
    client_id: clientId,
    type: event.type || "meeting",
    summary: event.summary || "",
    capital_discussion: Number(event.capital_discussion || 0),
    created_at: new Date().toISOString()
  };
  store.interactions = store.interactions || [];
  store.interactions.push(row);
  return row;
}