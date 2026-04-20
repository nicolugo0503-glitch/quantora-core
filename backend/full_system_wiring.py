from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime
import sqlite3
import os
import uuid
import hashlib

app = FastAPI(title="QNT30415 Full System Wiring", version="1.0.0")

BASE_DIR = os.path.dirname(__file__)
STATE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "state"))
DB_PATH = os.path.join(STATE_DIR, "quantora.db")

def now():
    return datetime.utcnow().isoformat() + "Z"

def conn():
    os.makedirs(STATE_DIR, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    return c

def init_db():
    c = conn()
    cur = c.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT UNIQUE, password TEXT, display_name TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS accounts (user_id TEXT PRIMARY KEY, capital REAL, pnl REAL)")
    cur.execute("CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id TEXT, created_at TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS trades (id TEXT PRIMARY KEY, user_id TEXT, symbol TEXT, side TEXT, qty REAL, price REAL, pnl REAL, created_at TEXT)")
    c.commit()
    c.close()

init_db()

RUNTIME = {
    "active_user_id": None,
    "active_user_email": None,
    "active_display_name": "Governance Admin",
    "allocated_capital": 0.0,
    "used_capital": 0.0,
    "remaining_capital": 0.0,
    "running_strategies": 0,
    "realized_pnl": 0.0,
    "risk_state": "SAFE",
    "broker_state": "paper_connected",
    "audit": [],
}

def log_event(kind: str, payload: Dict[str, Any]):
    evt = {
        "id": str(uuid.uuid4()),
        "kind": kind,
        "timestamp": now(),
        "payload": payload,
    }
    RUNTIME["audit"].append(evt)
    RUNTIME["audit"] = RUNTIME["audit"][-500:]
    return evt

def hash_pw(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()

def load_account(user_id: str):
    c = conn()
    cur = c.cursor()
    cur.execute("SELECT capital, pnl FROM accounts WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    c.close()
    if not row:
        return {"capital": 0.0, "pnl": 0.0}
    return {"capital": float(row[0]), "pnl": float(row[1])}

def sync_runtime_from_user(user_id: str):
    c = conn()
    cur = c.cursor()
    cur.execute("SELECT email, display_name FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    c.close()
    if not row:
        raise HTTPException(status_code=404, detail={"reason": "user_not_found"})
    acct = load_account(user_id)
    RUNTIME["active_user_id"] = user_id
    RUNTIME["active_user_email"] = row[0]
    RUNTIME["active_display_name"] = row[1] or row[0]
    RUNTIME["allocated_capital"] = round(acct["capital"], 2)
    RUNTIME["used_capital"] = 0.0
    RUNTIME["remaining_capital"] = round(acct["capital"], 2)
    RUNTIME["realized_pnl"] = round(acct["pnl"], 2)
    return {
        "user_id": user_id,
        "email": row[0],
        "display_name": row[1] or row[0],
        "capital": acct["capital"],
        "pnl": acct["pnl"],
    }

class Register(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = None

class Login(BaseModel):
    email: str
    password: str

class SessionBind(BaseModel):
    token: str

class TradeRecord(BaseModel):
    token: str
    symbol: str
    side: str
    qty: float
    price: float
    pnl: float = 0.0

@app.post("/platform/register")
def register(payload: Register):
    c = conn()
    cur = c.cursor()
    user_id = str(uuid.uuid4())
    try:
        cur.execute(
            "INSERT INTO users VALUES (?,?,?,?)",
            (user_id, payload.email, hash_pw(payload.password), payload.display_name or payload.email.split('@')[0]),
        )
        cur.execute("INSERT INTO accounts VALUES (?,?,?)", (user_id, 10000.0, 0.0))
        c.commit()
    except sqlite3.IntegrityError:
        c.close()
        raise HTTPException(status_code=400, detail={"reason": "user_exists"})
    c.close()
    evt = log_event("user_registered", {"user_id": user_id, "email": payload.email})
    return {"status": "ok", "user_id": user_id, "event": evt}

@app.post("/platform/login")
def login(payload: Login):
    c = conn()
    cur = c.cursor()
    cur.execute("SELECT id, password FROM users WHERE email=?", (payload.email,))
    row = cur.fetchone()
    if not row or row[1] != hash_pw(payload.password):
        c.close()
        raise HTTPException(status_code=401, detail={"reason": "invalid_credentials"})
    token = str(uuid.uuid4())
    cur.execute("INSERT INTO sessions VALUES (?,?,?)", (token, row[0], now()))
    c.commit()
    c.close()
    evt = log_event("user_logged_in", {"user_id": row[0], "email": payload.email})
    return {"status": "ok", "token": token, "user_id": row[0], "event": evt}

@app.post("/platform/session/bind")
def bind_session(payload: SessionBind):
    c = conn()
    cur = c.cursor()
    cur.execute("SELECT user_id FROM sessions WHERE token=?", (payload.token,))
    row = cur.fetchone()
    c.close()
    if not row:
        raise HTTPException(status_code=401, detail={"reason": "invalid_session"})
    bound = sync_runtime_from_user(row[0])
    evt = log_event("session_bound_to_runtime", {"user_id": row[0]})
    return {"status": "ok", "bound": bound, "event": evt}

@app.get("/platform/runtime/status")
def runtime_status():
    return {
        "mission": "QNT30415",
        "operator": RUNTIME["active_display_name"],
        "active_user_email": RUNTIME["active_user_email"],
        "allocated_capital": RUNTIME["allocated_capital"],
        "used_capital": RUNTIME["used_capital"],
        "remaining_capital": RUNTIME["remaining_capital"],
        "running_strategies": RUNTIME["running_strategies"],
        "realized_pnl": RUNTIME["realized_pnl"],
        "risk_state": RUNTIME["risk_state"],
        "broker_state": RUNTIME["broker_state"],
        "audit_events": len(RUNTIME["audit"]),
    }

@app.get("/platform/account/{user_id}")
def account(user_id: str):
    acct = load_account(user_id)
    return {"user_id": user_id, "capital": acct["capital"], "pnl": acct["pnl"]}

@app.post("/platform/trade/record")
def record_trade(payload: TradeRecord):
    c = conn()
    cur = c.cursor()
    cur.execute("SELECT user_id FROM sessions WHERE token=?", (payload.token,))
    row = cur.fetchone()
    if not row:
        c.close()
        raise HTTPException(status_code=401, detail={"reason": "invalid_session"})
    user_id = row[0]
    trade_id = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO trades VALUES (?,?,?,?,?,?,?,?)",
        (trade_id, user_id, payload.symbol.upper(), payload.side.lower(), payload.qty, payload.price, payload.pnl, now())
    )
    cur.execute("UPDATE accounts SET pnl=pnl+?, capital=capital+? WHERE user_id=?", (payload.pnl, payload.pnl, user_id))
    c.commit()
    c.close()
    bound = sync_runtime_from_user(user_id)
    RUNTIME["used_capital"] = round(abs(payload.qty * payload.price), 2)
    RUNTIME["remaining_capital"] = round(RUNTIME["allocated_capital"] - RUNTIME["used_capital"], 2)
    evt = log_event("trade_recorded_into_runtime", {"trade_id": trade_id, "user_id": user_id, "symbol": payload.symbol, "pnl": payload.pnl})
    return {"status": "ok", "trade_id": trade_id, "runtime": bound, "event": evt}

@app.get("/platform/trades/{user_id}")
def trades(user_id: str):
    c = conn()
    cur = c.cursor()
    cur.execute("SELECT id, symbol, side, qty, price, pnl, created_at FROM trades WHERE user_id=? ORDER BY created_at DESC", (user_id,))
    rows = cur.fetchall()
    c.close()
    return {"trades": [
        {"id": r[0], "symbol": r[1], "side": r[2], "qty": r[3], "price": r[4], "pnl": r[5], "created_at": r[6]}
        for r in rows
    ]}

@app.get("/platform/audit")
def audit(limit: int = 50):
    return {"events": RUNTIME["audit"][-limit:][::-1]}
