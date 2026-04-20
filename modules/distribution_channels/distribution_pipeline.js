export function createDistributionRecord(store, input){
  const row = {
    record_id: input.record_id || `DIST_${Date.now()}`,
    channel_id: input.channel_id || null,
    product_id: input.product_id || null,
    prospect_name: input.prospect_name || "Unknown Prospect",
    stage: input.stage || "introduced",
    target_commitment: Number(input.target_commitment || 0),
    created_at: new Date().toISOString()
  };
  store.pipeline = store.pipeline || [];
  store.pipeline.push(row);
  return row;
}

export function advanceDistributionPipeline(store, recordId, stage){
  store.pipeline = store.pipeline || [];
  const row = store.pipeline.find(x => x.record_id === recordId);
  if (!row) return { ok:false, error:"record_not_found" };
  row.stage = stage;
  row.updated_at = new Date().toISOString();
  return { ok:true, record: row };
}