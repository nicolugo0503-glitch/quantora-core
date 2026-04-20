from fastapi import APIRouter, Body, HTTPException, Request
from pathlib import Path
import json, time, hashlib, hmac, os

router = APIRouter(tags=["payment-provider"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
PROVIDER_DIR = ARTIFACTS_DIR / "user_payment_provider"
WEBHOOK_DIR = ARTIFACTS_DIR / "payment_webhooks"

PROVIDER_NAME = os.getenv("QUANTORA_PAYMENT_PROVIDER", "stripe_simulated")
WEBHOOK_SECRET = os.getenv("QUANTORA_PAYMENT_WEBHOOK_SECRET", "quantora-dev-webhook-secret")

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _funding():
    from backend.app import qnt30565_funding_router as funding
    return funding

def _safe_email(email: str) -> str:
    return hashlib.sha256((email or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _provider_path(email: str) -> Path:
    PROVIDER_DIR.mkdir(parents=True, exist_ok=True)
    return PROVIDER_DIR / f"{_safe_email(email)}.json"

def _webhook_path() -> Path:
    WEBHOOK_DIR.mkdir(parents=True, exist_ok=True)
    return WEBHOOK_DIR / "webhook_events.json"

def _require_user():
    mu = _mu()
    return mu._require_session()

def _load_provider(email: str) -> dict:
    path = _provider_path(email)
    if not path.exists():
        data = {
            "email": email,
            "provider": PROVIDER_NAME,
            "customer_id": None,
            "connected": False,
            "payment_methods": [],
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save_provider(email: str, data: dict) -> dict:
    data["updated_at"] = int(time.time())
    _provider_path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _load_webhooks() -> dict:
    path = _webhook_path()
    if not path.exists():
        data = {"events": []}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save_webhooks(data: dict) -> dict:
    _webhook_path().write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _create_customer_id(email: str) -> str:
    return "cus_" + hashlib.sha256((email or "").encode("utf-8")).hexdigest()[:18]

def _create_external_intent(amount: float, email: str, method_id: str | None) -> dict:
    return {
        "provider": PROVIDER_NAME,
        "external_intent_id": "extpi_" + hashlib.sha256(f"{email}:{amount}:{time.time()}".encode("utf-8")).hexdigest()[:18],
        "client_secret": "secret_" + hashlib.sha256(f"{email}:{amount}:secret".encode("utf-8")).hexdigest()[:24],
        "amount": round(float(amount), 2),
        "currency": "USD",
        "method_id": method_id,
        "status": "requires_confirmation_simulated",
        "created_at": int(time.time()),
    }

def _verify_signature(raw_body: bytes, signature: str) -> bool:
    digest = hmac.new(WEBHOOK_SECRET.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature or "")

@router.get("/api/user-payment-provider/status")
def user_payment_provider_status():
    session = _require_user()
    email = session.get("email")
    return _load_provider(email)

@router.post("/api/user-payment-provider/connect")
def user_payment_provider_connect(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    provider = _load_provider(email)
    provider["provider"] = (payload.get("provider") or PROVIDER_NAME).strip().lower()
    provider["connected"] = True
    provider["customer_id"] = provider.get("customer_id") or _create_customer_id(email)
    provider = _save_provider(email, provider)
    return {"status": "connected", "provider_profile": provider}

@router.post("/api/user-payment-provider/method")
def user_payment_provider_add_method(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    provider = _load_provider(email)
    if not provider.get("connected"):
        raise HTTPException(status_code=400, detail="Payment provider not connected")
    method = {
        "provider_method_id": "pmext_" + hashlib.sha256(f"{email}:{time.time()}".encode("utf-8")).hexdigest()[:18],
        "type": (payload.get("type") or "bank").strip().lower(),
        "label": (payload.get("label") or "External Method").strip(),
        "status": "attached_simulated",
        "created_at": int(time.time()),
    }
    provider.setdefault("payment_methods", []).append(method)
    provider = _save_provider(email, provider)
    return {"status": "attached", "method": method, "provider_profile": provider}

@router.post("/api/user-payment-provider/deposit-intent")
def user_payment_provider_deposit_intent(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    amount = round(float(payload.get("amount") or 0.0), 2)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")
    provider = _load_provider(email)
    if not provider.get("connected"):
        raise HTTPException(status_code=400, detail="Payment provider not connected")
    funding = _funding()
    intents = funding._load_intents(email)
    method_id = payload.get("method_id") or (provider.get("payment_methods") or [{}])[0].get("provider_method_id")
    external = _create_external_intent(amount, email, method_id)
    intent = {
        "intent_id": "pi_" + hashlib.sha256(f"{email}:{amount}:{time.time()}".encode("utf-8")).hexdigest()[:18],
        "type": "deposit",
        "amount": amount,
        "currency": "USD",
        "provider": provider.get("provider"),
        "provider_customer_id": provider.get("customer_id"),
        "provider_method_id": method_id,
        "external_intent_id": external["external_intent_id"],
        "client_secret": external["client_secret"],
        "status": "requires_confirmation_simulated",
        "created_at": int(time.time()),
    }
    intents.setdefault("payment_intents", []).insert(0, intent)
    intents["payment_intents"] = intents["payment_intents"][:100]
    funding._save_intents(email, intents)
    return {"status": "created", "intent": intent, "provider_profile": provider}

@router.post("/api/user-payment-provider/confirm")
def user_payment_provider_confirm(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    intent_id = payload.get("intent_id")
    funding = _funding()
    intents = funding._load_intents(email)
    intent = next((x for x in intents.get("payment_intents", []) if x.get("intent_id") == intent_id), None)
    if not intent:
        raise HTTPException(status_code=404, detail="Payment intent not found")
    if str(intent.get("status")).startswith("completed"):
        raise HTTPException(status_code=400, detail="Intent already completed")
    intent["status"] = "provider_confirmed_simulated"
    intent["provider_confirmed_at"] = int(time.time())
    funding._save_intents(email, intents)
    return {"status": "confirmed", "intent": intent}

@router.post("/api/payment-provider/webhook")
async def payment_provider_webhook(request: Request):
    raw = await request.body()
    signature = request.headers.get("x-quantora-signature", "")
    if not _verify_signature(raw, signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    payload = json.loads(raw.decode("utf-8"))
    event_type = (payload.get("type") or "").strip().lower()
    email = (payload.get("email") or "").strip().lower()
    intent_id = payload.get("intent_id")
    if not email or not intent_id:
        raise HTTPException(status_code=400, detail="Webhook missing email or intent_id")
    funding = _funding()
    intents = funding._load_intents(email)
    intent = next((x for x in intents.get("payment_intents", []) if x.get("intent_id") == intent_id), None)
    if not intent:
        raise HTTPException(status_code=404, detail="Payment intent not found")
    if event_type == "payment_intent.succeeded":
        mu = _mu()
        ledger = mu._load_ledger(email)
        amount = round(float(intent.get("amount") or 0.0), 2)
        ledger["balance"] = float(ledger.get("balance", 0.0)) + amount
        ledger["available"] = float(ledger.get("available", 0.0)) + amount
        ledger.setdefault("history", []).insert(0, {
            "type": "deposit",
            "amount": amount,
            "timestamp": int(time.time()),
            "source": "provider_webhook_simulated"
        })
        mu._save_ledger(email, ledger)
        mu._perf_snapshot(email, ledger)
        intent["status"] = "completed_via_webhook"
        intent["completed_at"] = int(time.time())
    else:
        intent["status"] = event_type or "received"
    funding._save_intents(email, intents)
    store = _load_webhooks()
    store.setdefault("events", []).insert(0, {
        "type": event_type,
        "email": email,
        "intent_id": intent_id,
        "received_at": int(time.time()),
        "payload": payload,
    })
    store["events"] = store["events"][:200]
    _save_webhooks(store)
    return {"status": "processed", "event_type": event_type, "intent_id": intent_id}

@router.get("/api/payment-provider/webhooks")
def payment_provider_webhooks():
    _require_user()
    return _load_webhooks()
