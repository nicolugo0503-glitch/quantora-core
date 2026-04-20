export function detectRiskClusters(exposures = []) {
  const rows = exposures.filter(x => Number(x.correlation || 0) >= 0.75).map(x => ({
    key: x.key || x.strategy_id || "UNKNOWN",
    correlation: Number(x.correlation || 0)
  }));
  return { cluster_count: rows.length, rows };
}