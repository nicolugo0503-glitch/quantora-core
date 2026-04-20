export function computeChannelPerformance(store, channelId, period){
  const rows = (store.pipeline || []).filter(x => x.channel_id === channelId);
  const conversions = rows.filter(x => x.stage === "capital_closed");
  const totalCapital = conversions.reduce((s,x)=>s+Number(x.target_commitment||0),0);
  return {
    channel_id: channelId,
    period: period || "UNSPECIFIED",
    prospects: rows.length,
    conversions: conversions.length,
    capital_raised: totalCapital,
    average_ticket: conversions.length ? Number((totalCapital / conversions.length).toFixed(2)) : 0
  };
}