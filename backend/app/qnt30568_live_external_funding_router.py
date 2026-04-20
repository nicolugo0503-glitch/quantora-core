from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, os, hashlib, hmac

router = APIRouter(tags=["live-external-funding"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
DEPLOY_DIR = ARTIFACTS_DIR / "live_external_funding_deployment"

def _pp():
    from backend.app import qnt30566_payment_provider_router as pp
    return pp

def _act():
    from backend.app import qnt30567_live_provider_activation_router as act
    return act

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _safe_email(email: str) -> str:
    return hashlib.sha256((email or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    DEPLOY_DIR.mkdir(parents=True, exist_ok=True)
    return DEPLOY_DIR / f"{_safe_email(email)}.json"

def _require_user():
    mu = _mu()
    return mu._require_session()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "deployment_status": "not_started",
            "provider": None,
            "mode": "simulated",
            "live_ready": False,
            "live_enabled": False,
            "checks": [],
            "last_deploy_check_at": None,
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email: str, data: dict) -> dict:
    data["updated_at"] = int(time.time())
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _provider_live_env(provider: str) -> dict:
    provider = (provider or "").strip().lower()
    if provider == "stripe":
        return {
            "secret": bool(os.getenv("STRIPE_SECRET_KEY")),
            "publishable": bool(os.getenv("STRIPE_PUBLISHABLE_KEY")),
            "webhook": bool(os.getenv("STRIPE_WEBHOOK_SECRET")),
        }
    if provider == "dwolla":
        return {
            "secret": bool(os.getenv("DWOLLA_SECRET")),
            "publishable": bool(os.getenv("DWOLLA_KEY")),
            "webhook": bool(os.getenv("DWOLLA_WEBHOOK_SECRET")),
        }
    return {"secret": False, "publishable": False, "webhook": False}

def _build(email: str) -> dict:
    act = _act()
    pp = _pp()
    activation = act._compute_status(email)
    provider_profile = pp._load_provider(email)
    provider = activation.get("provider") or provider_profile.get("provider")
    env = _provider_live_env(provider)
    checks = [
        {"name": "provider_selected", "ok": bool(provider)},
        {"name": "customer_ready", "ok": bool(activation.get("customer_ready"))},
        {"name": "methods_ready", "ok": bool(activation.get("methods_ready"))},
        {"name": "env_secret_ready", "ok": bool(env.get("secret"))},
        {"name": "env_publishable_ready", "ok": bool(env.get("publishable"))},
        {"name": "webhook_secret_ready", "ok": bool(env.get("webhook"))},
    ]
    live_ready = all(x["ok"] for x in checks) and provider in {"stripe", "dwolla"}
    mode = "live" if live_ready else "simulated"
    deployment_status = "live_ready" if live_ready else "activation_required"
    payload = _load(email)
    payload.update({
        "provider": provider,
        "mode": mode,
        "live_ready": live_ready,
        "deployment_status": deployment_status,
        "checks": checks,
        "last_deploy_check_at": int(time.time()),
        "provider_profile": provider_profile,
        "activation": activation,
    })
    return _save(email, payload)

@router.get("/api/live-funding-deployment/status")
def live_funding_deployment_status():
    session = _require_user()
    return _build(session.get("email"))

@router.post("/api/live-funding-deployment/check")
def live_funding_deployment_check():
    session = _require_user()
    return _build(session.get("email"))

@router.post("/api/live-funding-deployment/enable")
def live_funding_deployment_enable(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    state = _build(email)
    force = bool(payload.get("force", False))
    if not state.get("live_ready") and not force:
        raise HTTPException(status_code=400, detail="Provider not live-ready")
    state["live_enabled"] = True
    state["deployment_status"] = "live_enabled"
    return _save(email, state)

@router.post("/api/live-funding-deployment/disable")
def live_funding_deployment_disable():
    session = _require_user()
    email = session.get("email")
    state = _load(email)
    state["live_enabled"] = False
    state["deployment_status"] = "live_disabled"
    return _save(email, state)

@router.get("/api/live-funding-deployment/env-template")
def live_funding_deployment_env_template():
    _require_user()
    return {
        "QUANTORA_PAYMENT_PROVIDER": "stripe or dwolla",
        "STRIPE_SECRET_KEY": "",
        "STRIPE_PUBLISHABLE_KEY": "",
        "STRIPE_WEBHOOK_SECRET": "",
        "DWOLLA_KEY": "",
        "DWOLLA_SECRET": "",
        "DWOLLA_WEBHOOK_SECRET": "",
    }
