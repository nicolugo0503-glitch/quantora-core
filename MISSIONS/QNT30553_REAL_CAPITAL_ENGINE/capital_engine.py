
import json, os, time

LEDGER_FILE = os.path.join(os.path.dirname(__file__), "capital_ledger.json")

def _load():
    if not os.path.exists(LEDGER_FILE):
        return {"balance":0,"available":0,"allocated":0,"history":[]}
    with open(LEDGER_FILE,"r") as f:
        return json.load(f)

def _save(data):
    with open(LEDGER_FILE,"w") as f:
        json.dump(data,f,indent=2)

def get_capital():
    return _load()

def deposit(amount):
    d=_load()
    d["balance"]+=amount
    d["available"]+=amount
    d["history"].append({"type":"deposit","amount":amount,"ts":time.time()})
    _save(d)
    return d

def withdraw(amount):
    d=_load()
    if amount>d["available"]:
        raise ValueError("insufficient available balance")
    d["balance"]-=amount
    d["available"]-=amount
    d["history"].append({"type":"withdraw","amount":amount,"ts":time.time()})
    _save(d)
    return d
