import datetime
import importlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

REQUIRED_ARTIFACTS = [
    "users.json",
    "session.json",
    "billing_state.json",
]
REQUIRED_DB_COLUMNS = {
    "users": [
        "id",
        "email",
        "password_hash",
        "display_name",
        "operator_id",
        "plan",
        "subscription_status",
    ],
    "accounts": ["id", "user_id", "balance", "currency"],
    "trades": ["id", "user_id", "symbol", "side", "qty", "price"],
}
RUNTIME_MODULES = [
    "backend.qnt30417_billing",
    "backend.qnt30418_performance_attribution",
    "backend.full_system_wiring",
    "backend.execution_engine",
]


def now_iso() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def detect_environment() -> str:
    explicit = (os.getenv("QUANTORA_ENV") or os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or "").strip().lower()
    if explicit in {"local", "development", "dev"}:
        return "local"
    if explicit in {"staging", "stage", "preview"}:
        return "staging"
    if explicit in {"production", "prod"}:
        return "production"
    if os.getenv("RAILWAY_ENVIRONMENT"):
        return "production"
    if os.getenv("RAILWAY_PUBLIC_DOMAIN"):
        return "staging"
    return "local"


def execution_mode() -> str:
    return (os.getenv("QUANTORA_EXECUTION_MODE") or os.getenv("EXECUTION_MODE") or "paper").strip().lower()


def billing_mode() -> str:
    have_keys = all(
        [
            bool((os.getenv("STRIPE_SECRET_KEY") or "").strip()),
            bool((os.getenv("STRIPE_PUBLISHABLE_KEY") or "").strip()),
            bool((os.getenv("STRIPE_WEBHOOK_SECRET") or "").strip()),
        ]
    )
    return "live" if have_keys else "simulated"


def _ok(name: str, detail: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = {"name": name, "status": "ok", "detail": detail}
    if extra:
        payload["extra"] = extra
    return payload


def _warn(name: str, detail: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = {"name": name, "status": "warning", "detail": detail}
    if extra:
        payload["extra"] = extra
    return payload


def _critical(name: str, detail: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = {"name": name, "status": "critical", "detail": detail}
    if extra:
        payload["extra"] = extra
    return payload




def _is_writable_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".qnt_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def resolve_runtime_db_path(preferred: Path, artifacts_dir: Optional[Path] = None) -> Path:
    env_path = (os.getenv("QUANTORA_DB_PATH") or "").strip()
    if env_path:
        candidate = Path(env_path)
        candidate.parent.mkdir(parents=True, exist_ok=True)
        os.environ["QUANTORA_DB_PATH"] = str(candidate)
        return candidate

    preferred = Path(preferred)
    if _is_writable_dir(preferred.parent):
        os.environ["QUANTORA_DB_PATH"] = str(preferred)
        return preferred

    if artifacts_dir is not None and _is_writable_dir(Path(artifacts_dir)):
        candidate = Path(artifacts_dir) / "quantora.db"
        os.environ["QUANTORA_DB_PATH"] = str(candidate)
        return candidate

    fallback_root = Path("/tmp/quantora")
    fallback_root.mkdir(parents=True, exist_ok=True)
    candidate = fallback_root / "quantora.db"
    os.environ["QUANTORA_DB_PATH"] = str(candidate)
    return candidate


def bootstrap_sqlite(db_path: Path) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE,
                password TEXT,
                password_hash TEXT,
                display_name TEXT,
                operator_id TEXT,
                plan TEXT DEFAULT 'free',
                subscription_status TEXT DEFAULT 'active'
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                balance REAL DEFAULT 0,
                currency TEXT DEFAULT 'USD',
                capital REAL DEFAULT 0,
                pnl REAL DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                symbol TEXT,
                side TEXT,
                qty REAL,
                price REAL,
                pnl REAL DEFAULT 0,
                created_at TEXT
            )
            """
        )
        for table, columns in REQUIRED_DB_COLUMNS.items():
            cur.execute(f"PRAGMA table_info({table})")
            actual = {row[1] for row in cur.fetchall()}
            for col in columns:
                if col in actual:
                    continue
                col_type = "REAL" if col in {"balance", "qty", "price"} else "TEXT"
                default = " DEFAULT 0" if col_type == "REAL" else " DEFAULT ''"
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}{default}")
                checks.append(_warn(f"db.bootstrap.{table}.{col}", "Missing column created automatically during startup hardening"))
        conn.commit()
        checks.append(_ok("db.bootstrap", "SQLite bootstrap and schema self-heal completed", {"db_path": str(db_path)}))
    finally:
        conn.close()
    return checks

def env_checks() -> List[Dict[str, Any]]:
    env = detect_environment()
    base_url = (os.getenv("QUANTORA_APP_BASE_URL") or "").strip()
    railway_domain = (os.getenv("RAILWAY_PUBLIC_DOMAIN") or "").strip()
    inferred_base_url = ""
    if not base_url and railway_domain:
        inferred_base_url = railway_domain if railway_domain.startswith("http") else f"https://{railway_domain}"
        os.environ["QUANTORA_APP_BASE_URL"] = inferred_base_url
        base_url = inferred_base_url
    checks: List[Dict[str, Any]] = []
    checks.append(_ok("environment.classifier", f"Environment classified as {env}", {"environment": env}))
    if env == "production" and not base_url:
        checks.append(_warn("env.base_url", "QUANTORA_APP_BASE_URL missing in production; startup allowed in guarded mode until a canonical base URL is configured"))
    elif not base_url:
        checks.append(_warn("env.base_url", "QUANTORA_APP_BASE_URL not set; local fallback URLs will be used"))
    else:
        detail = "Base URL inferred from Railway public domain" if inferred_base_url else "Base URL present"
        checks.append(_ok("env.base_url", detail, {"base_url": base_url}))

    mode = billing_mode()
    if mode == "live":
        price_pro = bool((os.getenv("STRIPE_PRICE_PRO") or "").strip())
        price_inst = bool((os.getenv("STRIPE_PRICE_INSTITUTIONAL") or "").strip())
        if not (price_pro and price_inst):
            checks.append(_critical("env.stripe_prices", "Live billing selected but price IDs are missing"))
        else:
            checks.append(_ok("env.stripe_prices", "Stripe live billing configuration present"))
    else:
        checks.append(_warn("env.billing_mode", "Billing is running in simulated mode until live Stripe keys are configured", {"billing_mode": mode}))

    exec_mode = execution_mode()
    if env == "production" and exec_mode == "live" and mode != "live":
        checks.append(_critical("env.live_execution", "Live execution cannot run without live Stripe billing readiness"))
    else:
        checks.append(_ok("env.execution_mode", f"Execution mode is {exec_mode}", {"execution_mode": exec_mode}))
    return checks


def artifacts_checks(artifacts_dir: Path) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    for filename in REQUIRED_ARTIFACTS:
        path = artifacts_dir / filename
        if path.exists():
            checks.append(_ok(f"artifact.{filename}", "Artifact file present"))
        else:
            default = {"created_at": now_iso(), "generated_by": "QNT30420"}
            try:
                path.write_text(json.dumps(default, indent=2), encoding="utf-8")
                checks.append(_warn(f"artifact.{filename}", "Artifact file was missing and has been created"))
            except Exception as exc:
                checks.append(_critical(f"artifact.{filename}", f"Artifact file missing and could not be created: {exc}"))
    probe = artifacts_dir / ".qnt30420_write_probe"
    try:
        probe.write_text(now_iso(), encoding="utf-8")
        probe.unlink(missing_ok=True)
        checks.append(_ok("artifact.writeability", "Artifact directory is writable"))
    except Exception as exc:
        checks.append(_critical("artifact.writeability", f"Artifact directory not writable: {exc}"))
    return checks


def db_checks(db_path: Path, artifacts_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    env = detect_environment()
    resolved_db_path = resolve_runtime_db_path(db_path, artifacts_dir)
    if resolved_db_path != db_path:
        checks.append(_warn("db.path", "Runtime database path was redirected to a writable location", {"requested": str(db_path), "resolved": str(resolved_db_path)}))
    db_path = resolved_db_path
    try:
        checks.extend(bootstrap_sqlite(db_path))
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        for table, columns in REQUIRED_DB_COLUMNS.items():
            cursor.execute(f"PRAGMA table_info({table})")
            rows = cursor.fetchall()
            actual = {row[1] for row in rows}
            missing = [col for col in columns if col not in actual]
            if missing:
                msg = f"Missing required columns: {', '.join(missing)}"
                checks.append(_critical(f"db.table.{table}", msg) if env == "production" else _warn(f"db.table.{table}", msg))
            else:
                checks.append(_ok(f"db.table.{table}", "Required columns present"))
        conn.execute("SELECT 1")
        checks.append(_ok("db.query", "Database connectivity verified"))
    except Exception as exc:
        checks.append(_critical("db.connectivity", f"Database check failed: {exc}") if env == "production" else _warn("db.connectivity", f"Database check failed: {exc}"))
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return checks


def runtime_checks() -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    for mod in RUNTIME_MODULES:
        try:
            importlib.import_module(mod)
            checks.append(_ok(f"runtime.{mod}", "Module importable"))
        except Exception as exc:
            checks.append(_critical(f"runtime.{mod}", f"Module failed to import: {exc}"))
    return checks


def compute_readiness(checks: List[Dict[str, Any]]) -> Dict[str, Any]:
    critical = [c for c in checks if c["status"] == "critical"]
    warnings = [c for c in checks if c["status"] == "warning"]
    if critical:
        overall = "blocked"
    elif warnings:
        overall = "degraded"
    else:
        overall = "ready"
    return {
        "overall_status": overall,
        "critical_count": len(critical),
        "warning_count": len(warnings),
        "ok_count": len([c for c in checks if c["status"] == "ok"]),
        "readiness_score": max(0, 100 - (len(critical) * 35) - (len(warnings) * 8)),
    }


def safe_mode_summary(state: Dict[str, Any]) -> Dict[str, Any]:
    overall = state.get("overall_status", "unknown")
    enabled = overall in {"blocked", "degraded"}
    return {
        "enabled": enabled,
        "mode": "read_only" if overall == "blocked" else ("guarded" if overall == "degraded" else "normal"),
        "live_execution_allowed": overall == "ready" and execution_mode() == "live",
        "paper_execution_allowed": overall != "blocked",
        "capital_allocation_allowed": overall != "blocked",
        "reporting_allowed": True,
    }


def evaluate(artifacts_dir: Path, db_path: Path) -> Dict[str, Any]:
    checks = []
    checks.extend(env_checks())
    checks.extend(artifacts_checks(artifacts_dir))
    checks.extend(db_checks(db_path, artifacts_dir))
    checks.extend(runtime_checks())
    readiness = compute_readiness(checks)
    payload = {
        "mission": "QNT30420",
        "evaluated_at": now_iso(),
        "environment": detect_environment(),
        "billing_mode": billing_mode(),
        "execution_mode": execution_mode(),
        **readiness,
        "checks": checks,
    }
    payload["safe_mode"] = safe_mode_summary(payload)
    return payload


def summarize_for_health(report: Dict[str, Any], section_prefix: Optional[str] = None) -> Dict[str, Any]:
    checks = report.get("checks", [])
    if section_prefix:
        checks = [c for c in checks if c.get("name", "").startswith(section_prefix)]
    critical = sum(1 for c in checks if c.get("status") == "critical")
    warnings = sum(1 for c in checks if c.get("status") == "warning")
    status = "ok"
    if critical:
        status = "blocked"
    elif warnings:
        status = "warning"
    return {
        "status": status,
        "critical_count": critical,
        "warning_count": warnings,
        "checks": checks,
    }


def should_block_startup(report: Dict[str, Any]) -> bool:
    if os.getenv("QUANTORA_ALLOW_UNSAFE_STARTUP", "").strip().lower() in {"1", "true", "yes"}:
        return False
    return report.get("environment") == "production" and report.get("overall_status") == "blocked"
