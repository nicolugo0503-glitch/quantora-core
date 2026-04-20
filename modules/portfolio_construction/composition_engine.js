export function generatePortfolioComposition(strategies){
  return strategies.map(s=>({strategy:s.id, weight:s.weight||0}));
}