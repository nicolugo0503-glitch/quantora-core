export function computeClientHealth(store, clientId){
  const client = (store.clients || []).find(x => x.client_id === clientId);
  if (!client) return { ok:false, error:"client_not_found" };
  const interactions = (store.interactions || []).filter(x => x.client_id === clientId);
  const recentActivityScore = interactions.length >= 3 ? 20 : interactions.length * 6;
  const engagement = Number(client.engagement_score || 0);
  const capitalRatio = client.potential_capital > 0 ? Math.min(20, (client.current_capital / client.potential_capital) * 20) : 10;
  const score = Number((engagement * 0.6 + recentActivityScore + capitalRatio).toFixed(2));
  return {
    client_id: clientId,
    score,
    band: score >= 75 ? "expanding" : score >= 55 ? "stable" : "at_risk"
  };
}