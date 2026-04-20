export function computeDomainHealth(domain, metrics = {}){
  const base = Number(metrics.base_score || 75);
  const penalties = Number(metrics.penalties || 0);
  const score = Math.max(0, Math.min(100, base - penalties));
  return {
    domain,
    score,
    band: score >= 85 ? "strong" : score >= 65 ? "watch" : "degraded"
  };
}