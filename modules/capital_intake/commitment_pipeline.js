/**
 * Commitment processing pipeline.
 */

import { evaluateInvestor } from "./access_control.js";

export function processApplication(registry, applicationId) {
  registry.applications = registry.applications || [];
  const application = registry.applications.find(x => x.application_id === applicationId);
  if (!application) {
    return { ok: false, error: "application_not_found" };
  }
  const decision = evaluateInvestor(application);
  application.reviewed_at = new Date().toISOString();
  application.status = decision.eligible ? "approved" : "rejected";
  application.tier = decision.tier;
  application.decision_reasons = decision.reasons;
  return { ok: true, application, decision };
}
