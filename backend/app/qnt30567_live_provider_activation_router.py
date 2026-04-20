from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib, os

router = APIRouter(tags=["live-provider-activation"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ACTIVATION_DIR = ARTIFACTS_DIR / "payment_provider_activation"

SUPPORTED_PROVIDERS = {"stripe", "dwolla", "stripe_simulated", "dwolla_simulated"}

def _pp():
    from backend.app import qnt30566_payment_provider_router as pp
    return pp

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _safe_email(email: str) -> str:
    return hashlib.sha256((email or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _activation_path(email: str) -> Path:
    ACTIVATION_DIR.mkdir(parents=True, exist_ok=True)
    return ACTIVATION_DIR / f"{_safe_email(email)}.json"

def _require_user():
    mu = _mu()
    return mu._require_session()

def _load_activation(email: str) -> dict:
    path = _activation_path(email)
    if not path.exists():
        data = {
            "email": email,
            "provider": None,
            "mode": "simulated",
            "customer_ready": False,
            "methods_ready": False,
            "webhook_ready": False,
            "env_ready": False,
            "status": "not_started",
            "last_checked_at": None,
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save_activation(email: str, data: dict) -> dict:
    data["updated_at"] = int(time.time())
    _activation_path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _provider_env(provider: str) -> dict:
    provider = (provider or "").strip().lower()
    if provider.startswith("stripe"):
        secret = os.getenv("STRIPE_SECRET_KEY", "")
        publishable = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
        return {
            "provider": provider,
            "secret_present": bool(secret),
            "publishable_present": bool(publishable),
            "webhook_secret_present": bool(webhook_secret),
            "account_ready": bool(secret and publishable),
            "webhook_ready": bool(webhook_secret),
        }
    if provider.startswith("dwolla"):
        key = os.getenv("DWOLLA_KEY", "")
        secret = os.getenv("DWOLLA_SECRET", "")
        webhook_secret = os.getenv("DWOLLA_WEBHOOK_SECRET", "")
        return {
            "provider": provider,
            "secret_present": bool(secret),
            "publishable_present": bool(key),
            "webhook_secret_present": bool(webhook_secret),
            "account_ready": bool(key and secret),
            "webhook_ready": bool(webhook_secret),
        }
    return {
        "provider": provider,
        "secret_present": False,
        "publishable_present": False,
        "webhook_secret_present": False,
        "account_ready": False,
        "webhook_ready": False,
    }

def _compute_status(email: str) -> dict:
    pp = _pp()
    provider_profile = pp._load_provider(email)
    activation = _load_activation(email)
    provider = provider_profile.get("provider") or activation.get("provider") or os.getenv("QUANTORA_PAYMENT_PROVIDER", "stripe_simulated")
    env = _provider_env(provider)
    customer_ready = bool(provider_profile.get("customer_id"))
    methods_ready = bool(provider_profile.get("payment_methods"))
    webhook_ready = bool(env.get("webhook_ready"))
    env_ready = bool(env.get("account_ready"))
    mode = "live" if env_ready and webhook_ready and provider in {"stripe", "dwolla"} else "simulated"
    status = "activation_required"
    if customer_ready and methods_ready and env_ready and webhook_ready:
        status = "live_ready" if mode == "live" else "provider_ready_simulated"
    elif customer_ready or methods_ready:
        status = "partial"
    payload = {
        **activation,
        "provider": provider,
        "mode": mode,
        "customer_ready": customer_ready,
        "methods_ready": methods_ready,
        "webhook_ready": webhook_ready,
        "env_ready": env_ready,
        "status": status,
        "last_checked_at": int(time.time()),
        "provider_profile": provider_profile,
        "env": env,
    }
    _save_activation(email, payload)
    return payload

@router.get("/api/payment-provider-activation/status")
def payment_provider_activation_status():
    session = _require_user()
    email = session.get("email")
    return _compute_status(email)

@router.post("/api/payment-provider-activation/select")
def payment_provider_activation_select(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    provider = (payload.get("provider") or "").strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail="Unsupported provider")
    activation = _load_activation(email)
    activation["provider"] = provider
    _save_activation(email, activation)
    pp = _pp()
    provider_profile = pp._load_provider(email)
    provider_profile["provider"] = provider
    pp._save_provider(email, provider_profile)
    return _compute_status(email)

@router.post("/api/payment-provider-activation/check")
def payment_provider_activation_check():
    session = _require_user()
    email = session.get("email")
    return _compute_status(email)

@router.get("/api/payment-provider-activation/env")
def payment_provider_activation_env():
    session = _require_user()
    email = session.get("email")
    status = _compute_status(email)
    return status.get("env", {})

@router.post("/api/payment-provider-activation/mock-live")
def payment_provider_activation_mock_live():
    session = _require_user()
    email = session.get("email")
    activation = _load_activation(email)
    if not activation.get("provider"):
        activation["provider"] = "stripe_simulated"
    activation["mode"] = "live_mock"
    activation["customer_ready"] = True
    activation["methods_ready"] = True
    activation["webhook_ready"] = True
    activation["env_ready"] = True
    activation["status"] = "live_mock_ready"
    _save_activation(email, activation)
    return activation
