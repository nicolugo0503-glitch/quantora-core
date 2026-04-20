/**
 * Eligibility, access control, and investor tier classification.
 */

export function classifyInvestorTier(capitalIntent) {
  const amount = Number(capitalIntent || 0);
  if (amount >= 1000000) return "institutional";
  if (amount >= 100000) return "priority";
  if (amount >= 10000) return "qualified";
  return "entry";
}

export function evaluateInvestor(application) {
  const amount = Number(application.capital_intent || 0);
  const tier = classifyInvestorTier(amount);
  const eligible = amount >= 1000;
  return {
    eligible,
    tier,
    reasons: eligible
      ? ["minimum capital threshold satisfied"]
      : ["minimum capital threshold not met"]
  };
}
