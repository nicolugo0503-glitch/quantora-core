/**
 * Routes approved commitments into target vehicles with treasury-aware intent.
 */

export function routeCapitalCommitment(registry, commitment) {
  registry.routes = registry.routes || [];
  const route = {
    route_id: commitment.route_id || `ROUTE_${Date.now()}`,
    application_id: commitment.application_id || null,
    vehicle_id: commitment.vehicle_id || "VEHICLE_DEFAULT",
    approved_amount: Number(commitment.approved_amount || 0),
    route_status: commitment.route_status || "queued",
    created_at: new Date().toISOString()
  };
  registry.routes.push(route);
  return route;
}
