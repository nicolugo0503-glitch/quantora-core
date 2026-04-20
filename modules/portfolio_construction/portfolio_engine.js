export function createPortfolio(store, config){
  const p = {id:`PORT_${Date.now()}`, name:config.name, objective:config.objective, capital:config.capital||0, created:new Date().toISOString()};
  store.portfolios = store.portfolios||[];
  store.portfolios.push(p);
  return p;
}