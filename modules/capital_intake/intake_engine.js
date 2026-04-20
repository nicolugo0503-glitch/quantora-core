/**
 * QNT30640 Global Capital Intake System
 * Institutional intake engine for investor applications and capital commitments.
 */

export function submitApplication(registry, application) {
  const now = new Date().toISOString();
  const record = {
    application_id: application.application_id || `APP_${Date.now()}`,
    investor_name: application.investor_name || "Unknown Investor",
    email: application.email || "",
    requested_vehicle_id: application.requested_vehicle_id || "VEHICLE_DEFAULT",
    capital_intent: Number(application.capital_intent || 0),
    jurisdiction: application.jurisdiction || "UNSPECIFIED",
    investor_type: application.investor_type || "standard",
    submitted_at: now,
    status: "pending"
  };
  registry.applications = registry.applications || [];
  registry.applications.push(record);
  return record;
}

export function logCapitalInflow(registry, event) {
  registry.inflows = registry.inflows || [];
  const record = {
    inflow_id: event.inflow_id || `INFLOW_${Date.now()}`,
    application_id: event.application_id || null,
    investor_id: event.investor_id || null,
    vehicle_id: event.vehicle_id || "VEHICLE_DEFAULT",
    amount: Number(event.amount || 0),
    approved: Boolean(event.approved),
    timestamp: new Date().toISOString(),
    notes: event.notes || ""
  };
  registry.inflows.push(record);
  return record;
}
