export function routeSubscription(store, subscription){
  const row = {
    subscription_id: subscription.subscription_id || `SUB_${Date.now()}`,
    product_id: subscription.product_id || null,
    investor_id: subscription.investor_id || null,
    amount: Number(subscription.amount || 0),
    status: subscription.status || "pending",
    routed_at: new Date().toISOString()
  };
  store.subscriptions = store.subscriptions || [];
  store.subscriptions.push(row);
  return row;
}