# QNT30518 — Onboarding binding example
# Example only. Additive guidance, not auto-applied.

from fastapi import FastAPI

from MISSIONS.QNT30518_INVESTOR_ONBOARDING_SUBSCRIPTION_WORKFLOW.qnt30518_onboarding_engine import QNT30518InvestorOnboardingEngine
from MISSIONS.QNT30518_INVESTOR_ONBOARDING_SUBSCRIPTION_WORKFLOW.qnt30518_onboarding_router import build_qnt30518_router

app = FastAPI()

engine = QNT30518InvestorOnboardingEngine()
app.include_router(build_qnt30518_router(engine))
