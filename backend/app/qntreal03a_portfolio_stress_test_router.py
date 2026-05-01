import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/portfolio-stress-test", tags=["portfolio-stress-test"])

STATE_FILE = "real03a_portfolio_stress_test_state.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_state() -> Dict[str, Any]:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"mission": "QNT-REAL03A", "stress_test_status": "idle", "hard_blocked": True}


def _write_state(s: Dict[str, Any]) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(s, f, indent=2)


def _evaluate_blockers(s: Dict[str, Any]) -> List[str]:
    blockers = []
    if s.get("mission") != "QNT-REAL03A":
        blockers.append("State file mission mismatch — integrity not established")
    return blockers


class LoadScenariosRequest(BaseModel):
    scenarios: List[Dict[str, Any]]
    portfolio_id: Optional[str] = "DEFAULT-PORTFOLIO"
    actor: Optional[str] = "operator"


class ApplyShocksRequest(BaseModel):
    run_id: str
    actor: Optional[str] = "operator"


class ComputeVarRequest(BaseModel):
    run_id: str
    confidence: Optional[float] = 0.99
    actor: Optional[str] = "operator"


class AssessCapitalRequest(BaseModel):
    run_id: str
    capital_buffer_pct: Optional[float] = 0.08
    actor: Optional[str] = "operator"


class RunRequest(BaseModel):
    scenarios: List[Dict[str, Any]]
    portfolio_id: Optional[str] = "DEFAULT-PORTFOLIO"
    confidence: Optional[float] = 0.99
    capital_buffer_pct: Optional[float] = 0.08
    actor: Optional[str] = "operator"


@router.get("/health")
def health():
    return {"mission": "QNT-REAL03A", "status": "ok", "component": "portfolio-stress-test"}


@router.get("/summary")
def summary():
    s = _load_state()
    blockers = _evaluate_blockers(s)
    s["blockers"] = blockers
    s["hard_blocked"] = len(blockers) > 0
    return s


@router.post("/load-scenarios")
def load_scenarios(req: LoadScenariosRequest):
    run_id = f"STRESS-RUN-{uuid.uuid4().hex[:10].upper()}"
    s = _load_state()
    s["mission"] = "QNT-REAL03A"
    s["stress_test_status"] = "scenarios_loaded"
    s["run_id"] = run_id
    s["portfolio_id"] = req.portfolio_id
    s["scenarios"] = req.scenarios
    s["scenario_count"] = len(req.scenarios)
    s["loaded_at"] = _now()
    s["loaded_by"] = req.actor
    s["shocked_results"] = []
    s["var_99"] = None
    s["capital_assessment"] = None
    s["hard_blocked"] = False
    _write_state(s)
    return {
        "loaded": True,
        "run_id": run_id,
        "portfolio_id": req.portfolio_id,
        "scenario_count": len(req.scenarios),
    }


@router.post("/apply-shocks")
def apply_shocks(req: ApplyShocksRequest):
    s = _load_state()
    if s.get("run_id") != req.run_id:
        return {"shocks_applied": False, "error": "run_id mismatch"}
    if s.get("stress_test_status") != "scenarios_loaded":
        return {"shocks_applied": False, "error": f"must be in scenarios_loaded state, currently: {s.get('stress_test_status')}"}

    scenarios = s.get("scenarios", [])
    results = []
    for sc in scenarios:
        equity_shock = sc.get("equity_shock", -0.20)
        credit_shock = sc.get("credit_spread_shock", 0.01)
        estimated_pnl = equity_shock * 1_000_000 + credit_shock * -500_000
        results.append({
            "scenario_id": sc.get("scenario_id"),
            "scenario_name": sc.get("name"),
            "equity_shock_pct": equity_shock,
            "credit_spread_shock_bps": int(credit_shock * 10000),
            "estimated_pnl_usd": round(estimated_pnl, 2),
            "worst_case": estimated_pnl < -300_000,
        })

    s["stress_test_status"] = "shocks_applied"
    s["shocked_results"] = results
    s["shocks_applied_at"] = _now()
    s["shocks_applied_by"] = req.actor
    _write_state(s)
    return {
        "shocks_applied": True,
        "run_id": req.run_id,
        "scenario_count": len(results),
        "results": results,
    }


@router.post("/compute-var")
def compute_var(req: ComputeVarRequest):
    s = _load_state()
    if s.get("run_id") != req.run_id:
        return {"var_computed": False, "error": "run_id mismatch"}
    if s.get("stress_test_status") != "shocks_applied":
        return {"var_computed": False, "error": f"must be in shocks_applied state, currently: {s.get('stress_test_status')}"}

    results = s.get("shocked_results", [])
    pnls = [r.get("estimated_pnl_usd", 0) for r in results]
    if not pnls:
        return {"var_computed": False, "error": "no shocked results to compute VaR from"}

    pnls_sorted = sorted(pnls)
    idx = max(0, int((1 - req.confidence) * len(pnls_sorted)) - 1)
    var_99 = abs(pnls_sorted[idx])
    worst = min(pnls_sorted)

    s["stress_test_status"] = "var_computed"
    s["var_99"] = var_99
    s["var_confidence"] = req.confidence
    s["worst_scenario_pnl"] = worst
    s["var_computed_at"] = _now()
    s["var_computed_by"] = req.actor
    _write_state(s)
    return {
        "var_computed": True,
        "run_id": req.run_id,
        "confidence": req.confidence,
        "var_99": var_99,
        "worst_scenario_pnl": worst,
        "scenario_count": len(pnls),
    }


@router.post("/assess-capital")
def assess_capital(req: AssessCapitalRequest):
    s = _load_state()
    if s.get("run_id") != req.run_id:
        return {"assessed": False, "error": "run_id mismatch"}
    if s.get("stress_test_status") != "var_computed":
        return {"assessed": False, "error": f"must be in var_computed state, currently: {s.get('stress_test_status')}"}

    var_99 = s.get("var_99", 0)
    required_capital = var_99 * (1 + req.capital_buffer_pct)
    adequate = required_capital < 10_000_000

    assessment = {
        "var_99": var_99,
        "capital_buffer_pct": req.capital_buffer_pct,
        "required_capital_usd": round(required_capital, 2),
        "capital_adequate": adequate,
        "regulatory_breach": not adequate,
        "assessed_at": _now(),
    }
    s["stress_test_status"] = "assessed"
    s["capital_assessment"] = assessment
    s["last_run_id"] = s.get("run_id")
    s["assessed_by"] = req.actor
    _write_state(s)
    return {"assessed": True, "run_id": req.run_id, "assessment": assessment}


@router.post("/run")
def run_full(req: RunRequest):
    # Convenience: run all steps in sequence
    run_id = f"STRESS-RUN-{uuid.uuid4().hex[:10].upper()}"
    s = _load_state()
    s["mission"] = "QNT-REAL03A"
    s["run_id"] = run_id
    s["portfolio_id"] = req.portfolio_id
    s["scenarios"] = req.scenarios
    s["scenario_count"] = len(req.scenarios)
    s["loaded_at"] = _now()
    s["hard_blocked"] = False

    # Apply shocks
    results = []
    for sc in req.scenarios:
        equity_shock = sc.get("equity_shock", -0.20)
        credit_shock = sc.get("credit_spread_shock", 0.01)
        estimated_pnl = equity_shock * 1_000_000 + credit_shock * -500_000
        results.append({
            "scenario_id": sc.get("scenario_id"),
            "scenario_name": sc.get("name"),
            "equity_shock_pct": equity_shock,
            "credit_spread_shock_bps": int(credit_shock * 10000),
            "estimated_pnl_usd": round(estimated_pnl, 2),
            "worst_case": estimated_pnl < -300_000,
        })
    s["shocked_results"] = results

    # VaR
    pnls = sorted([r["estimated_pnl_usd"] for r in results])
    idx = max(0, int((1 - req.confidence) * len(pnls)) - 1)
    var_99 = abs(pnls[idx]) if pnls else 0
    s["var_99"] = var_99
    s["var_confidence"] = req.confidence
    s["worst_scenario_pnl"] = min(pnls) if pnls else 0

    # Capital
    required_capital = var_99 * (1 + req.capital_buffer_pct)
    adequate = required_capital < 10_000_000
    s["capital_assessment"] = {
        "var_99": var_99,
        "capital_buffer_pct": req.capital_buffer_pct,
        "required_capital_usd": round(required_capital, 2),
        "capital_adequate": adequate,
        "regulatory_breach": not adequate,
        "assessed_at": _now(),
    }
    s["stress_test_status"] = "assessed"
    s["last_run_id"] = run_id
    s["run_by"] = req.actor
    _write_state(s)
    return {
        "completed": True,
        "run_id": run_id,
        "scenario_count": len(results),
        "var_99": var_99,
        "capital_assessment": s["capital_assessment"],
        "results": results,
    }


@router.post("/reset")
def reset():
    _write_state({"mission": "QNT-REAL03A", "stress_test_status": "idle", "hard_blocked": False})
    return {"reset": True}
