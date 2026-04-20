export function updateClientStage(store, clientId, stage){
  store.clients = store.clients || [];
  const row = store.clients.find(x => x.client_id === clientId);
  if (!row) return { ok:false, error:"client_not_found" };
  row.relationship_status = stage;
  row.stage_updated_at = new Date().toISOString();
  return { ok:true, client: row };
}