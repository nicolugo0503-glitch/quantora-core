export function assignCoverage(store, clientId, ownerId){
  store.clients = store.clients || [];
  const row = store.clients.find(x => x.client_id === clientId);
  if (!row) return { ok:false, error:"client_not_found" };
  row.coverage_owner_id = ownerId;
  row.coverage_assigned_at = new Date().toISOString();
  return { ok:true, client: row };
}