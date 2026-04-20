
from fastapi import FastAPI
from datetime import datetime
import uuid

app = FastAPI(title="QNT30405 Fund OS Control Tower", version="1.0.0")

STATE={
 "systems":{
  "execution":"online",
  "strategies":"online",
  "capital":"online",
  "risk":"online",
  "treasury":"online",
  "governance":"online"
 },
 "global_mode":"autonomous",
 "alerts":[],
 "decisions":[],
 "audit":[]
}

def now(): return datetime.utcnow().isoformat()+"Z"

def log(kind,payload):
    STATE["audit"].append({"id":str(uuid.uuid4()),"kind":kind,"ts":now(),"payload":payload})
    STATE["audit"]=STATE["audit"][-500:]

@app.get("/control-tower/status")
def status():
    return {
        "mission":"QNT30405",
        "global_mode":STATE["global_mode"],
        "systems":STATE["systems"],
        "alert_count":len(STATE["alerts"]),
        "decision_count":len(STATE["decisions"]),
        "audit_events":len(STATE["audit"])
    }

@app.post("/control-tower/system/toggle")
def toggle(system:str, state:str):
    if system not in STATE["systems"]:
        return {"status":"error","reason":"unknown system"}
    STATE["systems"][system]=state
    log("system_toggle",{"system":system,"state":state})
    return {"status":"ok","systems":STATE["systems"]}

@app.post("/control-tower/alert")
def alert(message:str, severity:str="info"):
    a={"id":str(uuid.uuid4()),"message":message,"severity":severity,"ts":now()}
    STATE["alerts"].append(a)
    log("alert_created",a)
    return {"status":"ok","alert":a}

@app.post("/control-tower/decision")
def decision(summary:str):
    d={"id":str(uuid.uuid4()),"summary":summary,"ts":now()}
    STATE["decisions"].append(d)
    log("decision_recorded",d)
    return {"status":"ok","decision":d}

@app.get("/control-tower/audit")
def audit():
    return {"events":STATE["audit"][-50:][::-1]}

if __name__=="__main__":
    import uvicorn
    uvicorn.run("control_tower:app",host="127.0.0.1",port=8010)
