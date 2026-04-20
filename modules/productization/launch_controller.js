export function launchProduct(store, productId){
  store.products = store.products || [];
  const item = store.products.find(x => x.product_id === productId);
  if (!item) return { ok:false, error:"product_not_found" };
  item.status = "launched";
  item.launched_at = new Date().toISOString();
  return { ok:true, product:item };
}