import datetime
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any, Dict, Optional

PLAN_FEATURES = {
    "free": ["dashboard_basic", "paper_trading", "account_view"],
    "pro": [
        "dashboard_basic",
        "paper_trading",
        "account_view",
        "performance_engine",
        "strategy_competition",
        "runtime_orchestrator",
        "billing_portal",
        "performance_attribution",
    ],
    "institutional": [
        "dashboard_basic",
        "paper_trading",
        "account_view",
        "performance_engine",
        "strategy_competition",
        "runtime_orchestrator",
        "billing_portal",
        "performance_attribution",
        "live_bridge",
        "state_fabric",
        "api_gateway",
        "governance",
        "treasury",
        "multi_asset_routing",
        "live_execution",
        "operator_workspace",
    ],
}

PLAN_PRICING = {
    "free": {"price_usd": 0, "interval": "month"},
    "pro": {"price_usd": 299, "interval": "month"},
    "institutional": {"price_usd": 2500, "interval": "month"},
}

ACTIVE_STATUSES = {"active", "trialing", "free"}
PAID_PLANS = {"pro", "institutional"}
BILLING_GRACE_STATUSES = {"past_due"}


def now_iso() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def billing_defaults(user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    user = user or {}
    return {
        "plan": user.get("plan") or "free",
        "subscription_status": user.get("subscription_status") or "free",
        "stripe_customer_id": user.get("stripe_customer_id"),
        "subscription_id": user.get("subscription_id"),
        "current_period_end": user.get("current_period_end"),
        "billing_email": user.get("billing_email") or user.get("email"),
        "billing_updated_at": user.get("billing_updated_at"),
    }


def hydrate_user(user: Dict[str, Any]) -> Dict[str, Any]:
    hydrated = dict(user)
    hydrated.update(billing_defaults(user))
    return hydrated


def feature_allowed(user: Dict[str, Any], feature: str) -> bool:
    plan = hydrate_user(user).get("plan", "free")
    return feature in PLAN_FEATURES.get(plan, PLAN_FEATURES["free"])


def subscription_active(user: Dict[str, Any]) -> bool:
    status = hydrate_user(user).get("subscription_status", "free")
    return status in ACTIVE_STATUSES


def status_allows_execution(user: Dict[str, Any], execution_mode: str) -> bool:
    user = hydrate_user(user)
    mode = (execution_mode or "paper").lower()
    if mode == "live":
        return user.get("plan") == "institutional" and subscription_active(user)
    return user.get("subscription_status") in (ACTIVE_STATUSES | BILLING_GRACE_STATUSES)


def stripe_price_ids() -> Dict[str, Optional[str]]:
    return {
        "pro": (os.getenv("STRIPE_PRICE_PRO") or "").strip() or None,
        "institutional": (os.getenv("STRIPE_PRICE_INSTITUTIONAL") or "").strip() or None,
    }


def stripe_env_summary() -> Dict[str, Any]:
    prices = stripe_price_ids()
    return {
        "stripe_secret_key_present": bool(os.getenv("STRIPE_SECRET_KEY")),
        "stripe_publishable_key_present": bool(os.getenv("STRIPE_PUBLISHABLE_KEY")),
        "stripe_webhook_secret_present": bool(os.getenv("STRIPE_WEBHOOK_SECRET")),
        "stripe_price_pro_present": bool(prices.get("pro")),
        "stripe_price_institutional_present": bool(prices.get("institutional")),
    }


def stripe_live_ready() -> bool:
    env = stripe_env_summary()
    return all(env.values())


def stripe_mode() -> str:
    return "live" if stripe_live_ready() else "simulated"


def summarize_user(user: Dict[str, Any]) -> Dict[str, Any]:
    user = hydrate_user(user)
    plan = user.get("plan", "free")
    return {
        "plan": plan,
        "subscription_status": user.get("subscription_status", "free"),
        "stripe_customer_id": user.get("stripe_customer_id"),
        "subscription_id": user.get("subscription_id"),
        "current_period_end": user.get("current_period_end"),
        "billing_email": user.get("billing_email"),
        "allowed_features": PLAN_FEATURES.get(plan, PLAN_FEATURES["free"]),
        "price": PLAN_PRICING.get(plan, PLAN_PRICING["free"]),
        "is_execution_eligible": status_allows_execution(user, "paper"),
        "is_live_execution_eligible": status_allows_execution(user, "live"),
        "billing_mode": stripe_mode(),
    }


def _file(artifacts_dir: str, filename: str) -> str:
    os.makedirs(artifacts_dir, exist_ok=True)
    return os.path.join(artifacts_dir, filename)


def load_json(artifacts_dir: str, filename: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    path = _file(artifacts_dir, filename)
    if not os.path.exists(path):
        return fallback
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return fallback


def save_json(artifacts_dir: str, filename: str, data: Dict[str, Any]) -> None:
    path = _file(artifacts_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def ensure_state(artifacts_dir: str) -> Dict[str, Any]:
    state = load_json(
        artifacts_dir,
        "billing_state.json",
        {
            "mission": "QNT30417",
            "checkout_sessions": [],
            "portal_sessions": [],
            "webhooks": [],
            "audit": [],
            "metrics": {"last_computed_at": None},
        },
    )
    state.setdefault("mission", "QNT30417")
    state.setdefault("checkout_sessions", [])
    state.setdefault("portal_sessions", [])
    state.setdefault("webhooks", [])
    state.setdefault("audit", [])
    state.setdefault("metrics", {"last_computed_at": None})
    save_json(artifacts_dir, "billing_state.json", state)
    return state


def audit(artifacts_dir: str, kind: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    state = ensure_state(artifacts_dir)
    event = {
        "audit_id": f"bill_{uuid.uuid4().hex[:12]}",
        "kind": kind,
        "created_at": now_iso(),
        "payload": payload,
    }
    state["audit"].insert(0, event)
    state["audit"] = state["audit"][:500]
    save_json(artifacts_dir, "billing_state.json", state)
    return event


def _base_url() -> str:
    for env_name in ("QUANTORA_APP_BASE_URL", "APP_BASE_URL", "PUBLIC_BASE_URL"):
        value = (os.getenv(env_name) or "").strip()
        if value:
            return value.rstrip("/")
    railway_domain = (os.getenv("RAILWAY_PUBLIC_DOMAIN") or "").strip()
    if railway_domain:
        if railway_domain.startswith("http://") or railway_domain.startswith("https://"):
            return railway_domain.rstrip("/")
        return f"https://{railway_domain}"
    return ""


def absolute_url(url: str) -> str:
    raw = (url or "").strip() or "/billing.html"
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    base = _base_url()
    if base:
        return base + (raw if raw.startswith("/") else f"/{raw}")
    return f"http://127.0.0.1:8010{raw if raw.startswith('/') else '/' + raw}"


def stripe_api_request(method: str, path: str, form: Dict[str, Any]) -> Dict[str, Any]:
    secret = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
    if not secret:
        raise RuntimeError("stripe_secret_missing")
    encoded = urllib.parse.urlencode(form, doseq=True).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.stripe.com{path}",
        data=encoded,
        headers={
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method=method.upper(),
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        try:
            payload = json.loads(body)
            message = payload.get("error", {}).get("message") or body[:400]
        except Exception:
            message = body[:400]
        raise RuntimeError(f"stripe_http_{exc.code}: {message}")
    except Exception as exc:
        raise RuntimeError(f"stripe_connectivity_error: {exc}")


def ensure_stripe_customer(user: Dict[str, Any]) -> Optional[str]:
    user = hydrate_user(user)
    if user.get("stripe_customer_id"):
        return user.get("stripe_customer_id")
    if not stripe_live_ready():
        return None
    customer = stripe_api_request(
        "POST",
        "/v1/customers",
        {
            "email": user.get("billing_email") or user.get("email") or "unknown@quantora.local",
            "name": user.get("display_name") or user.get("email") or "Quantora Operator",
            "metadata[operator_id]": user.get("operator_id") or "",
            "metadata[plan]": user.get("plan") or "free",
        },
    )
    return customer.get("id")


def create_checkout_session(artifacts_dir: str, user: Dict[str, Any], plan: str, success_url: str, cancel_url: str) -> Dict[str, Any]:
    if plan not in PLAN_PRICING:
        raise ValueError("unknown_plan")
    user = hydrate_user(user)
    state = ensure_state(artifacts_dir)
    success = absolute_url(success_url)
    cancel = absolute_url(cancel_url)
    if plan in PAID_PLANS and stripe_live_ready():
        customer_id = user.get("stripe_customer_id") or ensure_stripe_customer(user)
        price_id = stripe_price_ids().get(plan)
        if not price_id:
            raise RuntimeError("stripe_price_missing")
        stripe_session = stripe_api_request(
            "POST",
            "/v1/checkout/sessions",
            {
                "mode": "subscription",
                "customer": customer_id,
                "success_url": success,
                "cancel_url": cancel,
                "client_reference_id": user.get("operator_id") or "",
                "line_items[0][price]": price_id,
                "line_items[0][quantity]": 1,
                "metadata[operator_id]": user.get("operator_id") or "",
                "metadata[plan]": plan,
                "subscription_data[metadata][operator_id]": user.get("operator_id") or "",
                "subscription_data[metadata][plan]": plan,
            },
        )
        session = {
            "checkout_session_id": stripe_session.get("id") or f"cs_{uuid.uuid4().hex[:18]}",
            "operator_id": user.get("operator_id"),
            "email": user.get("email"),
            "plan": plan,
            "status": stripe_session.get("status") or "open",
            "created_at": now_iso(),
            "success_url": success,
            "cancel_url": cancel,
            "checkout_url": stripe_session.get("url"),
            "price": PLAN_PRICING[plan],
            "mode": "live",
            "stripe_customer_id": customer_id,
        }
    else:
        session = {
            "checkout_session_id": f"cs_{uuid.uuid4().hex[:18]}",
            "operator_id": user.get("operator_id"),
            "email": user.get("email"),
            "plan": plan,
            "status": "open",
            "created_at": now_iso(),
            "success_url": success,
            "cancel_url": cancel,
            "checkout_url": f"/billing.html?session_id=cs_{uuid.uuid4().hex[:18]}&mode=simulated",
            "price": PLAN_PRICING[plan],
            "mode": "simulated",
            "stripe_customer_id": user.get("stripe_customer_id") or f"cus_{uuid.uuid4().hex[:10]}",
        }
    state["checkout_sessions"].insert(0, session)
    state["checkout_sessions"] = state["checkout_sessions"][:500]
    save_json(artifacts_dir, "billing_state.json", state)
    audit(artifacts_dir, "checkout_session_created", {"operator_id": user.get("operator_id"), "plan": plan, "mode": session.get("mode")})
    return session


def create_portal_session(artifacts_dir: str, user: Dict[str, Any], return_url: str) -> Dict[str, Any]:
    user = hydrate_user(user)
    state = ensure_state(artifacts_dir)
    return_target = absolute_url(return_url)
    if stripe_live_ready() and user.get("plan") in PAID_PLANS:
        customer_id = user.get("stripe_customer_id") or ensure_stripe_customer(user)
        stripe_portal = stripe_api_request(
            "POST",
            "/v1/billing_portal/sessions",
            {"customer": customer_id, "return_url": return_target},
        )
        portal = {
            "portal_session_id": stripe_portal.get("id") or f"bps_{uuid.uuid4().hex[:18]}",
            "operator_id": user.get("operator_id"),
            "email": user.get("email"),
            "created_at": now_iso(),
            "return_url": return_target,
            "portal_url": stripe_portal.get("url"),
            "mode": "live",
            "stripe_customer_id": customer_id,
        }
    else:
        portal = {
            "portal_session_id": f"bps_{uuid.uuid4().hex[:18]}",
            "operator_id": user.get("operator_id"),
            "email": user.get("email"),
            "created_at": now_iso(),
            "return_url": return_target,
            "portal_url": f"/billing.html?operator_id={user.get('operator_id')}",
            "mode": "simulated",
            "stripe_customer_id": user.get("stripe_customer_id"),
        }
    state["portal_sessions"].insert(0, portal)
    state["portal_sessions"] = state["portal_sessions"][:200]
    save_json(artifacts_dir, "billing_state.json", state)
    audit(artifacts_dir, "portal_session_created", {"operator_id": user.get("operator_id"), "mode": portal.get("mode")})
    return portal


def record_webhook(artifacts_dir: str, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    state = ensure_state(artifacts_dir)
    event = {
        "webhook_id": f"wh_{uuid.uuid4().hex[:18]}",
        "event_type": event_type,
        "created_at": now_iso(),
        "payload": payload,
    }
    state["webhooks"].insert(0, event)
    state["webhooks"] = state["webhooks"][:500]
    save_json(artifacts_dir, "billing_state.json", state)
    audit(artifacts_dir, "webhook_recorded", {"event_type": event_type, "operator_id": payload.get("operator_id")})
    return event


def _epoch_to_iso(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    try:
        return datetime.datetime.utcfromtimestamp(int(value)).date().isoformat()
    except Exception:
        return str(value)


def _status_from_event_type(event_type: str, obj: Dict[str, Any]) -> Optional[str]:
    if event_type == "invoice.payment_failed":
        return "past_due"
    if event_type == "customer.subscription.deleted":
        return "canceled"
    return obj.get("status") or None


def _plan_from_lookup(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    low = str(value).strip().lower()
    if low in PLAN_PRICING:
        return low
    price_ids = stripe_price_ids()
    for plan, pid in price_ids.items():
        if pid and value == pid:
            return plan
    return None


def derive_billing_update_from_stripe_event(event: Dict[str, Any]) -> Dict[str, Any]:
    data = (event or {}).get("data") or {}
    obj = data.get("object") or {}
    metadata = obj.get("metadata") or {}
    operator_id = metadata.get("operator_id") or obj.get("client_reference_id") or (event or {}).get("client_reference_id")

    plan = _plan_from_lookup(metadata.get("plan"))
    if not plan:
        price_id = None
        items = (obj.get("items") or {}).get("data") or []
        if items:
            price_info = items[0].get("price") or {}
            price_id = price_info.get("id")
        if not price_id:
            lines = (obj.get("lines") or {}).get("data") or []
            if lines:
                price_info = (lines[0].get("price") or {})
                price_id = price_info.get("id")
        plan = _plan_from_lookup(price_id)
    if not plan and obj.get("amount_total"):
        amt = int(obj.get("amount_total") or 0) / 100.0
        if round(amt) == PLAN_PRICING["pro"]["price_usd"]:
            plan = "pro"
        elif round(amt) == PLAN_PRICING["institutional"]["price_usd"]:
            plan = "institutional"
    if not plan:
        plan = "free"

    event_type = (event or {}).get("type") or "unknown"
    customer = obj.get("customer") or obj.get("customer_id")
    subscription_id = None
    if event_type.startswith("customer.subscription"):
        subscription_id = obj.get("id")
    elif event_type.startswith("checkout.session") or event_type.startswith("invoice."):
        subscription_id = obj.get("subscription")
    status = _status_from_event_type(event_type, obj) or ("active" if plan in PAID_PLANS else "free")
    period_end = _epoch_to_iso(obj.get("current_period_end"))

    return {
        "operator_id": operator_id,
        "plan": plan,
        "subscription_status": status,
        "stripe_customer_id": customer,
        "subscription_id": subscription_id,
        "current_period_end": period_end,
        "event_type": event_type,
        "raw_event_id": event.get("id"),
    }


def verify_stripe_signature(raw_body: bytes, signature_header: str, secret: Optional[str], tolerance: int = 300) -> bool:
    if not secret or not signature_header:
        return False
    parts = {}
    for piece in signature_header.split(","):
        if "=" in piece:
            k, v = piece.split("=", 1)
            parts.setdefault(k.strip(), []).append(v.strip())
    timestamps = parts.get("t") or []
    signatures = parts.get("v1") or []
    if not timestamps or not signatures:
        return False
    try:
        ts = int(timestamps[0])
    except Exception:
        return False
    if abs(int(time.time()) - ts) > tolerance:
        return False
    signed_payload = f"{ts}.".encode("utf-8") + raw_body
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, sig) for sig in signatures)


def parse_stripe_webhook(raw_body: bytes, signature_header: str) -> Dict[str, Any]:
    secret = (os.getenv("STRIPE_WEBHOOK_SECRET") or "").strip()
    if not verify_stripe_signature(raw_body, signature_header, secret):
        raise ValueError("invalid_signature")
    return json.loads(raw_body.decode("utf-8"))


def billing_metrics(users: list, state: Dict[str, Any]) -> Dict[str, Any]:
    hydrated_users = [hydrate_user(u) for u in (users or [])]
    active_paid = [u for u in hydrated_users if u.get("plan") in PAID_PLANS and u.get("subscription_status") in ACTIVE_STATUSES]
    grace_users = [u for u in hydrated_users if u.get("subscription_status") in BILLING_GRACE_STATUSES]
    canceled_users = [u for u in hydrated_users if str(u.get("subscription_status") or "").lower() in {"canceled", "unpaid"}]
    mrr = sum(PLAN_PRICING.get(u.get("plan"), {"price_usd": 0}).get("price_usd", 0) for u in active_paid)
    total_paid_hist = len(active_paid) + len(canceled_users)
    churn_rate = round((len(canceled_users) / total_paid_hist) * 100, 2) if total_paid_hist else 0.0
    metrics = {
        "mode": stripe_mode(),
        "mrr_usd": mrr,
        "active_paid_subscribers": len(active_paid),
        "active_pro": sum(1 for u in active_paid if u.get("plan") == "pro"),
        "active_institutional": sum(1 for u in active_paid if u.get("plan") == "institutional"),
        "grace_period_subscribers": len(grace_users),
        "churned_subscribers": len(canceled_users),
        "churn_rate_pct": churn_rate,
        "failed_payment_events": sum(1 for w in state.get("webhooks", []) if w.get("event_type") == "invoice.payment_failed"),
        "canceled_event_count": sum(1 for w in state.get("webhooks", []) if w.get("event_type") == "customer.subscription.deleted"),
        "total_users": len(hydrated_users),
        "computed_at": now_iso(),
    }
    return metrics
