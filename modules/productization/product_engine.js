export function createProduct(store, config){
  const row = {
    product_id: config.product_id || `PROD_${Date.now()}`,
    name: config.name || "Unnamed Product",
    portfolio_id: config.portfolio_id || null,
    vehicle_id: config.vehicle_id || null,
    structure: config.structure || "fund",
    status: config.status || "draft",
    created_at: new Date().toISOString()
  };
  store.products = store.products || [];
  store.products.push(row);
  return row;
}

export function listProducts(store){
  return (store.products || []).slice();
}