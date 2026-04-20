from fastapi import APIRouter, Body

router = APIRouter(tags=["governance"])

@router.get("/governance/ledger")
def governance_ledger():
    from backend.app import main as app_main
    admin = app_main.require_admin()
    return app_main.governance_ledger(admin)

@router.get("/governance/ledger/summary")
def governance_ledger_summary():
    from backend.app import main as app_main
    admin = app_main.require_admin()
    return app_main.governance_ledger_summary(admin)

@router.get("/policy-engine/policies")
def policy_engine_policies():
    from backend.app import main as app_main
    admin = app_main.require_admin()
    return app_main.policy_engine_policies(admin)

@router.post("/policy-engine/policies/update")
def policy_engine_policies_update(payload: dict = Body(...)):
    from backend.app import main as app_main
    admin = app_main.require_admin()
    model = app_main.PolicyUpdateRequest(**payload)
    return app_main.policy_engine_policies_update(model, admin)

@router.get("/approvals/queue")
def approvals_queue():
    from backend.app import main as app_main
    admin = app_main.require_admin()
    return app_main.approvals_queue(admin)

@router.post("/approvals/decision")
def approvals_decision(payload: dict = Body(...)):
    from backend.app import main as app_main
    admin = app_main.require_admin()
    model = app_main.ApprovalDecisionRequest(**payload)
    return app_main.approvals_decision(model, admin)
