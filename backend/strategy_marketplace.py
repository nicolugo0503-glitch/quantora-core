from datetime import datetime

def _now(): return datetime.utcnow().isoformat() + "Z"

_DB = {
    "strategies": [],
    "mandates": [],
    "allocations": []
}

def list_strategies():
    return {"strategies": _DB["strategies"]}

def publish_strategy(name, description, risk_profile):
    rec = {
        "strategy_id": f"str_{len(_DB['strategies'])+1:04d}",
        "name": name,
        "description": description,
        "risk_profile": risk_profile,
        "created_at": _now()
    }
    _DB["strategies"].append(rec)
    return rec

def create_mandate(strategy_id, capital_target, min_ticket):
    rec = {
        "mandate_id": f"man_{len(_DB['mandates'])+1:04d}",
        "strategy_id": strategy_id,
        "capital_target": float(capital_target),
        "min_ticket": float(min_ticket),
        "created_at": _now()
    }
    _DB["mandates"].append(rec)
    return rec

def allocate(mandate_id, investor_name, amount):
    rec = {
        "allocation_id": f"alloc_{len(_DB['allocations'])+1:04d}",
        "mandate_id": mandate_id,
        "investor_name": investor_name,
        "amount": float(amount),
        "created_at": _now()
    }
    _DB["allocations"].append(rec)
    return rec

def summary():
    return {
        "timestamp": _now(),
        "strategies": len(_DB["strategies"]),
        "mandates": len(_DB["mandates"]),
        "allocations": len(_DB["allocations"]),
        "allocated_capital": round(sum(x["amount"] for x in _DB["allocations"]),2)
    }
