export function buildMandate(config){
  return {objective:config.objective, risk_limit:config.risk_limit||50, target_vol:config.target_vol||10};
}