import { buildConcentrationMap } from "./concentration_map.js";
import { detectRiskClusters } from "./correlation_monitor.js";
import { runStressScenarios } from "./stress_scenarios.js";
import { computeFragilityScore } from "./fragility_scoring.js";

export function evaluateIncrementalRisk(store, action, context = {}) {
  const concentration = buildConcentrationMap(context.vehicle_id || "VEHICLE_DEFAULT", context);
  const clusters = detectRiskClusters(context.exposures || []);
  const stress = runStressScenarios(context.vehicle_id || "VEHICLE_DEFAULT", context);
  const fragility = computeFragilityScore(context.entity_id || context.vehicle_id || "VEHICLE_DEFAULT", context);
  const concentrationBreach = Number(concentration.top_weight || 0) > Number(context.max_single_exposure || 0.35);
  const fragilityBreach = Number(fragility.score || 0) >= Number(context.fragility_block_threshold || 75);
  const stressBreach = (stress.summary || []).some(x => Number(x.loss_pct || 0) >= Number(context.loss_block_threshold || 18));
  let decision = "approve";
  let reason = "risk posture acceptable";
  if (stressBreach || fragilityBreach) {
    decision = "block";
    reason = "stress or fragility threshold breached";
  } else if (concentrationBreach || clusters.cluster_count > Number(context.cluster_warn_threshold || 2)) {
    decision = "cap";
    reason = "concentration or dependency risk elevated";
  }
  store.risk_actions = store.risk_actions || [];
  const row = {
    action_id: action.action_id || `RISK_${Date.now()}`,
    vehicle_id: context.vehicle_id || "VEHICLE_DEFAULT",
    action_type: action.action_type || "allocation",
    amount: Number(action.amount || 0),
    decision,
    reason,
    timestamp: new Date().toISOString()
  };
  store.risk_actions.push(row);
  return { decision, reason, concentration, clusters, stress, fragility, audit: row };
}