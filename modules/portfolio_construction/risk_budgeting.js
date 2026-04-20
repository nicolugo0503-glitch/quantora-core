export function allocateRiskBudget(strategies){
  const total = strategies.reduce((s,x)=>s+x.score,0)||1;
  return strategies.map(s=>({...s, risk_weight:(s.score/total)}));
}