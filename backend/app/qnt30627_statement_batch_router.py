from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["investor-statement-batch-engine"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
STATEMENT_DIR = ARTIFACTS_DIR / "investor_statement_batch_engine"


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _identity():
    from backend.app import qnt30617_identity_registry_router as identity
    return identity


def _onboarding():
    from backend.app import qnt30623_onboarding_router as onboarding
    return onboarding


def _ledger():
    from backend.app import qnt30624_capital_ledger_router as ledger
    return ledger


def _waterfall():
    from backend.app import qnt30625_waterfall_router as waterfall
    return waterfall


def _equalization():
    from backend.app import qnt30626_equalization_router as equalization
    return equalization


def _pnl():
    from backend.app import qnt30586_pnl_ledger_router as pnl
    return pnl


def _execution():
    from backend.app import qnt30629_strategy_execution_router as execution
    return execution


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode()).hexdigest()[:24]


def _id(prefix: str) -> str:
    return f"{prefix}_{time.time_ns()}"


def _path(email: str) -> Path:
    STATEMENT_DIR.mkdir(parents=True, exist_ok=True)
    return STATEMENT_DIR / f"{_safe(email)}.json"


def _require_user():
    return _mu()._require_session()


def _now_ts() -> int:
    return int(time.time())


def _current_period() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _parse_period(period: str):
    raw = (period or "").strip()
    if len(raw) != 7 or raw[4] != "-":
        raise HTTPException(status_code=400, detail="period must be YYYY-MM")
    try:
        year = int(raw[:4])
        month = int(raw[5:7])
        start = datetime(year, month, 1, tzinfo=timezone.utc)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid period") from exc
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return raw, int(start.timestamp()), int(end.timestamp())


def _in_period(ts, period: str) -> bool:
    if ts in (None, ""):
        return False
    try:
        value = int(ts)
    except Exception:
        return False
    _p, start, end = _parse_period(period)
    return start <= value < end


def _load(email: str) -> dict:
    p = _path(email)
    if not p.exists():
        data = {
            "email": email,
            "periods": {},
            "batch_runs": [],
            "created_at": _now_ts(),
            "updated_at": _now_ts(),
        }
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(p.read_text(encoding="utf-8"))


def _save(email: str, data: dict) -> dict:
    data["updated_at"] = _now_ts()
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def _ordered_periods(data: dict):
    return [data["periods"][k] for k in sorted(data.get("periods", {}).keys(), reverse=True)]


def _latest_period_snapshot(data: dict):
    ordered = _ordered_periods(data)
    return ordered[0] if ordered else None


def _investor_universe(email: str):
    identity_data = _identity()._load(email)
    onboarding_data = _onboarding()._load(email)
    ledger_data = _ledger()._load(email)
    eq_data = _equalization()._load(email)

    by_id = {}

    for item in identity_data.get("investors", []):
        investor_id = str(item.get("investor_id") or "").strip()
        if investor_id:
            by_id.setdefault(investor_id, {})["identity"] = item

    for item in onboarding_data.get("investors", []):
        investor_id = str(item.get("investor_id") or "").strip()
        if investor_id:
            by_id.setdefault(investor_id, {})["onboarding"] = item

    for item in ledger_data.get("accounts", []):
        investor_id = str(item.get("investor_id") or "").strip()
        if investor_id:
            by_id.setdefault(investor_id, {})["account"] = item

    for item in eq_data.get("series_accounts", []):
        investor_id = str(item.get("investor_id") or "").strip()
        if investor_id and investor_id in by_id and "series" not in by_id[investor_id]:
            by_id[investor_id]["series"] = item
        elif investor_id:
            by_id.setdefault(investor_id, {})["series"] = item

    output = []
    for investor_id, payload in by_id.items():
        output.append({
            "investor_id": investor_id,
            "identity": payload.get("identity"),
            "onboarding": payload.get("onboarding"),
            "account": payload.get("account"),
            "series": payload.get("series"),
        })
    output.sort(key=lambda x: (x.get("identity") or {}).get("legal_name") or (x.get("onboarding") or {}).get("name") or investor_id)
    return output


def _signed_amount(event: dict) -> float:
    amount = round(float(event.get("amount") or 0.0), 2)
    event_type = str(event.get("event_type") or "").lower()
    if event_type in {"credit", "subscription_adjustment"}:
        return amount
    return -amount


def _round_money(v) -> float:
    return round(float(v or 0.0), 2)


def _round_units(v) -> float:
    return round(float(v or 0.0), 8)


def _sleeve_rollup(email: str):
    pnl_data = _pnl()._load(email)
    positions = pnl_data.get("positions", []) or []
    rollup = {}
    for pos in positions:
        sleeve_id = str(pos.get("sleeve_id") or "").strip()
        if not sleeve_id:
            continue
        item = rollup.setdefault(sleeve_id, {
            "sleeve_id": sleeve_id,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "position_count": 0,
        })
        item["realized_pnl"] = _round_money(item["realized_pnl"] + float(pos.get("realized_pnl") or 0.0))
        item["unrealized_pnl"] = _round_money(item["unrealized_pnl"] + float(pos.get("unrealized_pnl") or 0.0))
        item["position_count"] += 1
    for item in rollup.values():
        item["total_pnl"] = _round_money(item["realized_pnl"] + item["unrealized_pnl"])
    return rollup


def _allocation_performance(email: str, ledger_data: dict, investor_id: str, period: str | None = None):
    try:
        if _execution()._has_live_execution(email):
            detailed = [
                row for row in _execution()._investor_strategy_attribution(email, period)
                if row.get('investor_id') == investor_id
            ]
            if detailed:
                return [
                    {
                        'allocation_id': row.get('allocation_map_id'),
                        'strategy': row.get('strategy_name') or row.get('strategy_id'),
                        'sleeve': row.get('sleeve') or 'main',
                        'amount': _round_money(row.get('amount') or 0.0),
                        'status': row.get('status') or 'active',
                        'sleeve_total_amount': _round_money(row.get('strategy_total_capital') or 0.0),
                        'sleeve_total_pnl': _round_money((row.get('pnl_amount') or 0.0) / (row.get('investor_share_ratio') or 1.0)) if float(row.get('investor_share_ratio') or 0.0) > 0 else _round_money(row.get('pnl_amount') or 0.0),
                        'investor_share_ratio': round(float(row.get('investor_share_ratio') or 0.0), 8),
                        'pnl_amount': _round_money(row.get('pnl_amount') or 0.0),
                        'return_pct': round(float(row.get('return_pct') or 0.0), 4),
                        'data_quality': row.get('data_quality') or 'live_trade_attribution',
                        'created_at': row.get('created_at'),
                    }
                    for row in detailed
                ]
    except Exception:
        pass

    allocations = [a for a in (ledger_data.get("allocations", []) or []) if a.get("investor_id") == investor_id]
    sleeve_totals = {}
    for row in ledger_data.get("allocations", []) or []:
        sleeve = str(row.get("sleeve") or "main")
        sleeve_totals[sleeve] = _round_money(sleeve_totals.get(sleeve, 0.0) + float(row.get("amount") or 0.0))

    rollup = _sleeve_rollup(email)
    out = []
    for alloc in allocations:
        sleeve = str(alloc.get("sleeve") or "main")
        strategy = str(alloc.get("strategy") or "core")
        amount = _round_money(alloc.get("amount") or 0.0)
        sleeve_total_amount = _round_money(sleeve_totals.get(sleeve, 0.0))
        sleeve_pnl = _round_money((rollup.get(sleeve) or {}).get("total_pnl") or 0.0)
        investor_share_ratio = (amount / sleeve_total_amount) if sleeve_total_amount > 0 else 0.0
        pnl_amount = _round_money(sleeve_pnl * investor_share_ratio)
        return_pct = round((pnl_amount / amount) * 100.0, 4) if amount > 0 else 0.0
        out.append({
            "allocation_id": alloc.get("allocation_id"),
            "strategy": strategy,
            "sleeve": sleeve,
            "amount": amount,
            "status": alloc.get("status") or "active",
            "sleeve_total_amount": sleeve_total_amount,
            "sleeve_total_pnl": sleeve_pnl,
            "investor_share_ratio": round(investor_share_ratio, 8),
            "pnl_amount": pnl_amount,
            "return_pct": return_pct,
            "data_quality": "live" if sleeve in rollup else "pending_execution_mapping",
            "created_at": alloc.get("created_at"),
        })
    out.sort(key=lambda x: x.get("amount") or 0.0, reverse=True)
    return out


def _reconciliation_snapshot(ledger_data: dict, eq_data: dict):
    accounts = ledger_data.get("accounts", []) or []
    entries = ledger_data.get("entries", []) or []
    total_nav = _round_money(sum(float(a.get("nav") or 0.0) for a in accounts))
    total_committed = _round_money(sum(float(a.get("committed_capital") or 0.0) for a in accounts))
    total_funded = _round_money(sum(float(a.get("funded_capital") or 0.0) for a in accounts))
    net_entries = _round_money(sum(float(e.get("amount") or 0.0) for e in entries))
    total_series_capital = _round_money(sum(float(s.get("capital_amount") or 0.0) for s in (eq_data.get("series_accounts", []) or [])))
    nav_vs_entries_gap = _round_money(total_nav - net_entries)
    nav_vs_series_gap = _round_money(total_nav - total_series_capital)
    status = "pass"
    if not accounts:
        status = "fail"
    elif abs(nav_vs_entries_gap) > 0.01 or abs(nav_vs_series_gap) > max(0.01, total_nav * 0.35):
        status = "warning"
    return {
        "status": status,
        "account_count": len(accounts),
        "entry_count": len(entries),
        "total_committed_capital": total_committed,
        "total_funded_capital": total_funded,
        "total_nav": total_nav,
        "total_series_capital": total_series_capital,
        "nav_vs_entries_gap": nav_vs_entries_gap,
        "nav_vs_series_gap": nav_vs_series_gap,
        "checked_at": _now_ts(),
    }


def _statement_for_investor(email: str, period: str, envelope: dict, ledger_data: dict, waterfall_data: dict, eq_data: dict):
    investor_id = envelope.get("investor_id")
    identity = envelope.get("identity") or {}
    onboarding = envelope.get("onboarding") or {}
    account = envelope.get("account") or {}
    series = envelope.get("series") or {}
    entries = [e for e in ledger_data.get("entries", []) if e.get("investor_id") == investor_id]
    period_entries = [e for e in entries if _in_period(e.get("created_at"), period)]
    notices = [n for n in waterfall_data.get("distribution_notices", []) if n.get("investor_id") == investor_id and (_in_period(n.get("published_at"), period) or _in_period(n.get("created_at"), period))]
    eq_events = [e for e in eq_data.get("equalization_events", []) if e.get("investor_id") == investor_id and _in_period(e.get("created_at"), period)]
    allocations = _allocation_performance(email, ledger_data, investor_id, period)

    period_contributions = _round_money(sum(float(e.get("amount") or 0.0) for e in period_entries if float(e.get("amount") or 0.0) > 0))
    period_withdrawals = _round_money(abs(sum(float(e.get("amount") or 0.0) for e in period_entries if float(e.get("amount") or 0.0) < 0)))
    distribution_amount = _round_money(sum(float(n.get("distribution_amount") or 0.0) for n in notices if str(n.get("status") or "draft") in {"published", "draft"}))
    equalization_delta = _round_money(sum(_signed_amount(e) for e in eq_events))
    allocation_pnl = _round_money(sum(float(a.get("pnl_amount") or 0.0) for a in allocations))
    net_return_amount = _round_money(allocation_pnl + equalization_delta)

    current_eq_credit = _round_money(series.get("equalization_credit") or 0.0)
    funded_capital = _round_money(account.get("funded_capital") or 0.0)
    ending_nav = _round_money(max(0.0, funded_capital + allocation_pnl + current_eq_credit - distribution_amount))
    beginning_nav = _round_money(max(0.0, ending_nav - period_contributions + period_withdrawals - net_return_amount + distribution_amount))
    period_return_pct = round((net_return_amount / beginning_nav) * 100.0, 4) if beginning_nav > 0 else 0.0

    external_flow_count = len(period_entries) + len(notices)
    twr_pct = round((net_return_amount / beginning_nav) * 100.0, 4) if beginning_nav > 0 and external_flow_count == 0 else None
    twr_status = "computed" if twr_pct is not None else "valuation_series_required"

    investor_name = identity.get("legal_name") or onboarding.get("name") or account.get("investor_name") or investor_id
    share_class_id = series.get("share_class_id") or None
    share_class = next((c for c in (eq_data.get("share_classes", []) or []) if c.get("share_class_id") == share_class_id), None)

    activity = []
    for e in period_entries:
        activity.append({
            "timestamp": e.get("created_at"),
            "type": e.get("entry_type") or "entry",
            "amount": _round_money(e.get("amount") or 0.0),
            "description": e.get("description") or "Capital ledger entry",
            "source": "capital_ledger",
        })
    for n in notices:
        activity.append({
            "timestamp": n.get("published_at") or n.get("created_at"),
            "type": "distribution_notice",
            "amount": _round_money(n.get("distribution_amount") or 0.0),
            "description": f"Waterfall notice ({n.get('status') or 'draft'})",
            "source": "waterfall",
        })
    for e in eq_events:
        activity.append({
            "timestamp": e.get("created_at"),
            "type": e.get("event_type") or "equalization_event",
            "amount": _round_money(_signed_amount(e)),
            "description": f"Equalization {e.get('event_type')}",
            "source": "equalization",
        })
    activity.sort(key=lambda x: int(x.get("timestamp") or 0), reverse=True)

    return {
        "statement_id": _id("stmt"),
        "period": period,
        "generated_at": _now_ts(),
        "investor": {
            "investor_id": investor_id,
            "legal_name": investor_name,
            "primary_email": identity.get("primary_email") or "",
            "entity_type": identity.get("entity_type") or "investor",
            "jurisdiction": identity.get("jurisdiction") or "",
            "share_class_id": share_class_id,
            "share_class_name": (share_class or {}).get("class_name"),
            "series_id": series.get("series_id"),
            "series_name": series.get("series_name"),
            "account_id": account.get("account_id"),
        },
        "capital_summary": {
            "committed_capital": _round_money(account.get("committed_capital") or onboarding.get("commitment") or 0.0),
            "funded_capital": funded_capital,
            "unfunded_capital": _round_money(account.get("unfunded_capital") or 0.0),
            "nav": ending_nav,
            "ownership_pct": round(float(account.get("ownership_pct") or 0.0), 6),
        },
        "performance": {
            "beginning_nav": beginning_nav,
            "ending_nav": ending_nav,
            "net_return_amount": net_return_amount,
            "period_return_pct": period_return_pct,
            "twr_pct": twr_pct,
            "twr_status": twr_status,
            "allocation_pnl": allocation_pnl,
            "equalization_delta": equalization_delta,
            "external_flow_count": external_flow_count,
        },
        "allocations": allocations,
        "activity": activity,
        "waterfall": {
            "distribution_amount": distribution_amount,
            "notices": notices,
            "latest_run": (waterfall_data.get("runs") or [None])[0],
        },
        "equalization": {
            "series_id": series.get("series_id"),
            "series_name": series.get("series_name"),
            "nav_per_share": round(float(series.get("nav_per_share") or 0.0), 6),
            "units": _round_units(series.get("units") or 0.0),
            "equalization_credit": current_eq_credit,
            "period_events": eq_events,
        },
        "audit": {
            "period_entry_count": len(period_entries),
            "distribution_notice_count": len(notices),
            "equalization_event_count": len(eq_events),
            "allocation_count": len(allocations),
            "sources": ["identity_registry", "onboarding", "capital_ledger", "waterfall", "equalization", "pnl_ledger"],
        },
    }


def _build_period_snapshot(email: str, period: str):
    ledger_data = _ledger()._load(email)
    waterfall_data = _waterfall()._load(email)
    eq_data = _equalization()._load(email)
    investors = _investor_universe(email)
    reconciliation = _reconciliation_snapshot(ledger_data, eq_data)
    if not investors:
        raise HTTPException(status_code=400, detail="No investors available. Bootstrap demo data or onboard investors first.")

    statements = {}
    total_nav = 0.0
    total_returns = 0.0
    total_distributions = 0.0
    for inv in investors:
        stmt = _statement_for_investor(email, period, inv, ledger_data, waterfall_data, eq_data)
        statements[inv["investor_id"]] = stmt
        total_nav += float(stmt["capital_summary"].get("nav") or 0.0)
        total_returns += float(stmt["performance"].get("net_return_amount") or 0.0)
        total_distributions += float(stmt["waterfall"].get("distribution_amount") or 0.0)

    snapshot = {
        "batch_id": _id("batch"),
        "period": period,
        "generated_at": _now_ts(),
        "status": "open",
        "locked_at": None,
        "reconciliation": reconciliation,
        "summary": {
            "statement_count": len(statements),
            "total_nav": _round_money(total_nav),
            "total_net_return": _round_money(total_returns),
            "total_distributions": _round_money(total_distributions),
            "investor_ids": list(statements.keys()),
        },
        "statements": statements,
    }
    return snapshot


def _seed_demo(email: str, period: str):
    identity = _identity()
    onboarding = _onboarding()
    ledger = _ledger()
    waterfall = _waterfall()
    equalization = _equalization()
    pnl = _pnl()

    now = _now_ts()
    _p, start_ts, _end_ts = _parse_period(period)
    prev_ts = start_ts - (15 * 24 * 60 * 60)
    period_mid = start_ts + (10 * 24 * 60 * 60)

    investors = [
        {
            "investor_id": "inv_qnt_001",
            "legal_name": "Meridian Endowment Fund",
            "primary_email": "ops@meridianendowment.example",
            "entity_type": "institution",
            "jurisdiction": "US",
            "name": "Meridian Endowment Fund",
            "commitment": 500000.0,
            "funded": 420000.0,
            "ownership_pct": 43.75,
            "share_class_id": "class_qnta",
            "series_id": "series_qnta_001",
            "series_name": "Series 2026-01",
            "series_nav": 108.45,
            "eq_credit": -4200.0,
            "distribution": 18500.0,
            "allocations": [
                {"strategy": "Alpha Core", "sleeve": "alpha_core", "amount": 220000.0},
                {"strategy": "Macro FX", "sleeve": "macro_fx", "amount": 160000.0},
            ],
        },
        {
            "investor_id": "inv_qnt_002",
            "legal_name": "Aurora Family Office",
            "primary_email": "capital@aurorafamily.example",
            "entity_type": "family_office",
            "jurisdiction": "UK",
            "name": "Aurora Family Office",
            "commitment": 350000.0,
            "funded": 300000.0,
            "ownership_pct": 31.25,
            "share_class_id": "class_qnta",
            "series_id": "series_qnta_002",
            "series_name": "Series 2026-01",
            "series_nav": 107.10,
            "eq_credit": -2550.0,
            "distribution": 13200.0,
            "allocations": [
                {"strategy": "Alpha Core", "sleeve": "alpha_core", "amount": 140000.0},
                {"strategy": "Credit Income", "sleeve": "credit_income", "amount": 110000.0},
            ],
        },
        {
            "investor_id": "inv_qnt_003",
            "legal_name": "Northstar Treasury Partners",
            "primary_email": "ir@northstartreasury.example",
            "entity_type": "institution",
            "jurisdiction": "SG",
            "name": "Northstar Treasury Partners",
            "commitment": 250000.0,
            "funded": 240000.0,
            "ownership_pct": 25.0,
            "share_class_id": "class_qntb",
            "series_id": "series_qntb_003",
            "series_name": "Series 2026-02",
            "series_nav": 103.85,
            "eq_credit": 1750.0,
            "distribution": 9800.0,
            "allocations": [
                {"strategy": "Macro FX", "sleeve": "macro_fx", "amount": 100000.0},
                {"strategy": "Treasury Arbitrage", "sleeve": "treasury_arb", "amount": 90000.0},
            ],
        },
    ]

    identity_data = {
        "email": email,
        "investors": [
            {
                "investor_id": inv["investor_id"],
                "legal_name": inv["legal_name"],
                "primary_email": inv["primary_email"],
                "entity_type": inv["entity_type"],
                "jurisdiction": inv["jurisdiction"],
                "status": "active",
                "created_at": prev_ts,
            }
            for inv in investors
        ],
        "profiles": [
            {
                "profile_id": f"profile_{inv['investor_id']}",
                "profile_name": f"{inv['legal_name']} Primary Delivery",
                "investor_id": inv["investor_id"],
                "recipients": [{"name": inv["legal_name"], "email": inv["primary_email"], "role": "primary", "active": True}],
                "delivery_channels": ["portal", "email"],
                "status": "active",
                "created_at": prev_ts,
            }
            for inv in investors
        ],
        "created_at": now,
        "updated_at": now,
    }
    identity._save(email, identity_data)

    onboarding_data = {
        "email": email,
        "investors": [
            {
                "investor_id": inv["investor_id"],
                "name": inv["name"],
                "status": "active",
                "commitment": inv["commitment"],
                "checklist": {
                    "nda_signed": True,
                    "subscription_agreement": True,
                    "kyc_completed": True,
                    "accreditation_verified": True,
                    "capital_commitment": True,
                },
                "documents": [
                    {"doc_id": f"sub_{inv['investor_id']}", "type": "subscription", "name": "Subscription Agreement", "status": "uploaded", "created_at": prev_ts},
                    {"doc_id": f"kyc_{inv['investor_id']}", "type": "kyc", "name": "KYC Package", "status": "uploaded", "created_at": prev_ts},
                ],
                "created_at": prev_ts,
            }
            for inv in investors
        ],
        "created_at": now,
        "updated_at": now,
    }
    onboarding._save(email, onboarding_data)

    accounts = []
    entries = []
    allocations = []
    for inv in investors:
        accounts.append({
            "account_id": f"acct_{inv['investor_id']}",
            "investor_id": inv["investor_id"],
            "investor_name": inv["name"],
            "status": "open",
            "committed_capital": inv["commitment"],
            "funded_capital": inv["funded"],
            "unfunded_capital": _round_money(inv["commitment"] - inv["funded"]),
            "nav": inv["funded"],
            "ownership_pct": inv["ownership_pct"],
            "created_at": prev_ts,
            "updated_at": now,
        })
        entries.append({
            "entry_id": f"entry_{inv['investor_id']}",
            "investor_id": inv["investor_id"],
            "account_id": f"acct_{inv['investor_id']}",
            "entry_type": "funding",
            "amount": inv["funded"],
            "description": "Initial funding",
            "created_at": prev_ts,
        })
        for idx, alloc in enumerate(inv["allocations"], start=1):
            allocations.append({
                "allocation_id": f"alloc_{inv['investor_id']}_{idx}",
                "investor_id": inv["investor_id"],
                "strategy": alloc["strategy"],
                "sleeve": alloc["sleeve"],
                "amount": alloc["amount"],
                "status": "active",
                "created_at": prev_ts,
            })

    ledger_data = {
        "email": email,
        "accounts": accounts,
        "entries": entries,
        "allocations": allocations,
        "created_at": now,
        "updated_at": now,
    }
    ledger._save(email, ledger_data)

    waterfall_notices = []
    investor_allocations = []
    total_dist = 0.0
    for inv in investors:
        waterfall_notices.append({
            "notice_id": f"notice_{inv['investor_id']}_{period}",
            "investor_id": inv["investor_id"],
            "investor_name": inv["name"],
            "distribution_amount": inv["distribution"],
            "status": "published",
            "created_at": period_mid,
            "published_at": period_mid,
        })
        total_dist += inv["distribution"]
        investor_allocations.append({
            "investor_id": inv["investor_id"],
            "investor_name": inv["name"],
            "ownership_pct": inv["ownership_pct"],
            "funded_capital": inv["funded"],
            "distribution_amount": inv["distribution"],
            "account_id": f"acct_{inv['investor_id']}",
        })
    waterfall_data = {
        "email": email,
        "runs": [{
            "run_id": f"waterfall_{period}",
            "timestamp": period_mid,
            "total_nav": _round_money(sum(inv["funded"] for inv in investors)),
            "total_funded_capital": _round_money(sum(inv["funded"] for inv in investors)),
            "distributable_profit": total_dist,
            "hurdle_rate_pct": 8.0,
            "hurdle_amount": _round_money(sum(inv["funded"] for inv in investors) * 0.08),
            "gp_carry_pct": 20.0,
            "gp_carry_amount": 0.0,
            "lp_distribution_pool": total_dist,
            "investor_allocations": investor_allocations,
            "notice_count": len(waterfall_notices),
            "status": "calculated",
        }],
        "distribution_notices": waterfall_notices,
        "created_at": now,
        "updated_at": now,
    }
    waterfall._save(email, waterfall_data)

    share_classes = [
        {"share_class_id": "class_qnta", "class_name": "Class A", "base_nav_per_share": 100.0, "fee_rate_pct": 2.0, "currency": "USD", "status": "active", "created_at": prev_ts},
        {"share_class_id": "class_qntb", "class_name": "Class B", "base_nav_per_share": 100.0, "fee_rate_pct": 1.5, "currency": "USD", "status": "active", "created_at": prev_ts},
    ]
    series_accounts = []
    equalization_events = []
    for inv in investors:
        units = inv["funded"] / inv["series_nav"] if inv["series_nav"] > 0 else 0.0
        series_accounts.append({
            "series_id": inv["series_id"],
            "investor_id": inv["investor_id"],
            "share_class_id": inv["share_class_id"],
            "series_name": inv["series_name"],
            "capital_amount": _round_money(units * inv["series_nav"]),
            "nav_per_share": inv["series_nav"],
            "units": _round_units(units),
            "equalization_credit": inv["eq_credit"],
            "status": "active",
            "created_at": prev_ts,
            "updated_at": now,
        })
        if inv["eq_credit"] < 0:
            equalization_events.append({
                "event_id": f"eqevt_{inv['investor_id']}",
                "series_id": inv["series_id"],
                "investor_id": inv["investor_id"],
                "share_class_id": inv["share_class_id"],
                "event_type": "management_fee",
                "basis_amount": inv["funded"],
                "rate_pct": round(abs(inv["eq_credit"]) / inv["funded"] * 100.0, 6),
                "amount": abs(inv["eq_credit"]),
                "post_credit_balance": inv["eq_credit"],
                "created_at": period_mid,
            })
        else:
            equalization_events.append({
                "event_id": f"eqevt_{inv['investor_id']}",
                "series_id": inv["series_id"],
                "investor_id": inv["investor_id"],
                "share_class_id": inv["share_class_id"],
                "event_type": "credit",
                "basis_amount": inv["funded"],
                "rate_pct": round(abs(inv["eq_credit"]) / inv["funded"] * 100.0, 6),
                "amount": abs(inv["eq_credit"]),
                "post_credit_balance": inv["eq_credit"],
                "created_at": period_mid,
            })
    equalization_data = {
        "email": email,
        "share_classes": share_classes,
        "series_accounts": series_accounts,
        "equalization_events": equalization_events,
        "created_at": now,
        "updated_at": now,
    }
    equalization._save(email, equalization_data)

    pnl_data = {
        "email": email,
        "positions": [
            {"position_id": "pos_alpha_core", "sleeve_id": "alpha_core", "symbol": "SPY", "qty": 1000.0, "avg_price": 520.0, "mark_price": 542.0, "realized_pnl": 18000.0, "unrealized_pnl": 24000.0, "updated_at": now},
            {"position_id": "pos_macro_fx", "sleeve_id": "macro_fx", "symbol": "DX1", "qty": 40.0, "avg_price": 105.0, "mark_price": 112.0, "realized_pnl": 12000.0, "unrealized_pnl": 9000.0, "updated_at": now},
            {"position_id": "pos_credit_income", "sleeve_id": "credit_income", "symbol": "LQD", "qty": 1200.0, "avg_price": 108.0, "mark_price": 111.0, "realized_pnl": 6000.0, "unrealized_pnl": 4000.0, "updated_at": now},
            {"position_id": "pos_treasury_arb", "sleeve_id": "treasury_arb", "symbol": "IEF", "qty": 900.0, "avg_price": 94.0, "mark_price": 95.5, "realized_pnl": 3000.0, "unrealized_pnl": 1500.0, "updated_at": now},
        ],
        "ledger": [],
        "created_at": now,
        "updated_at": now,
    }
    pnl._save(email, pnl_data)

    return {
        "investor_count": len(investors),
        "period": period,
        "seeded_at": now,
    }


@router.get("/api/investor-statements")
def investor_statements_store():
    session = _require_user()
    return _load(session.get("email"))


@router.post("/api/investor-statements/bootstrap-demo")
def investor_statements_bootstrap(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    period = str((payload or {}).get("period") or _current_period())
    _parse_period(period)
    seeded = _seed_demo(email, period)
    return {"status": "seeded", "demo": seeded}


@router.post("/api/investor-statements/generate")
def investor_statements_generate(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    body = payload or {}
    period = str(body.get("period") or _current_period())
    _parse_period(period)
    if body.get("bootstrap_demo"):
        _seed_demo(email, period)
    data = _load(email)
    existing = (data.get("periods") or {}).get(period)
    if existing and existing.get("status") == "locked":
        raise HTTPException(status_code=409, detail="Reporting period is locked and immutable")
    snapshot = _build_period_snapshot(email, period)
    data.setdefault("periods", {})[period] = snapshot
    data.setdefault("batch_runs", []).insert(0, {
        "batch_id": snapshot.get("batch_id"),
        "period": period,
        "generated_at": snapshot.get("generated_at"),
        "status": snapshot.get("status"),
        "statement_count": snapshot.get("summary", {}).get("statement_count", 0),
        "reconciliation_status": snapshot.get("reconciliation", {}).get("status"),
    })
    data["batch_runs"] = data.get("batch_runs", [])[:200]
    _save(email, data)
    return {"status": "generated", "period": period, "snapshot": snapshot}


@router.post("/api/investor-statements/lock")
def investor_statements_lock(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    period = str(payload.get("period") or "")
    _parse_period(period)
    data = _load(email)
    snapshot = (data.get("periods") or {}).get(period)
    if not snapshot:
        snapshot = _build_period_snapshot(email, period)
        data.setdefault("periods", {})[period] = snapshot
    snapshot["status"] = "locked"
    snapshot["locked_at"] = _now_ts()
    for run in data.get("batch_runs", []):
        if run.get("period") == period:
            run["status"] = "locked"
            run["locked_at"] = snapshot["locked_at"]
    _save(email, data)
    return {"status": "locked", "period": period, "snapshot": snapshot}


@router.get("/api/investor-statements/summary")
def investor_statements_summary(period: str | None = None):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    ordered = _ordered_periods(data)
    selected = None
    if period:
        selected = (data.get("periods") or {}).get(period)
    if not selected:
        selected = ordered[0] if ordered else None
    periods = [
        {
            "period": item.get("period"),
            "batch_id": item.get("batch_id"),
            "status": item.get("status"),
            "generated_at": item.get("generated_at"),
            "locked_at": item.get("locked_at"),
            "statement_count": (item.get("summary") or {}).get("statement_count", 0),
            "total_nav": (item.get("summary") or {}).get("total_nav", 0.0),
            "total_net_return": (item.get("summary") or {}).get("total_net_return", 0.0),
            "total_distributions": (item.get("summary") or {}).get("total_distributions", 0.0),
            "reconciliation_status": (item.get("reconciliation") or {}).get("status"),
        }
        for item in ordered
    ]
    return {
        "email": email,
        "period_count": len(periods),
        "locked_period_count": sum(1 for p in periods if p.get("status") == "locked"),
        "batch_run_count": len(data.get("batch_runs", [])),
        "latest_period": periods[0] if periods else None,
        "selected_period": selected,
        "periods": periods,
        "batch_runs": data.get("batch_runs", [])[:100],
    }


@router.get("/api/investor-statements/period/{period}")
def investor_statements_period(period: str):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    snapshot = (data.get("periods") or {}).get(period)
    if not snapshot:
        raise HTTPException(status_code=404, detail="period not found")
    return snapshot


@router.get("/api/investor-statements/statement/{period}/{investor_id}")
def investor_statement_detail(period: str, investor_id: str):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    snapshot = (data.get("periods") or {}).get(period)
    if not snapshot:
        raise HTTPException(status_code=404, detail="period not found")
    statement = (snapshot.get("statements") or {}).get(investor_id)
    if not statement:
        raise HTTPException(status_code=404, detail="statement not found")
    return statement
