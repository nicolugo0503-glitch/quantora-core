
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import json, uuid, datetime

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent
ARTIFACTS_DIR = BACKEND_DIR / "artifacts"
FRONTEND_DIR = PROJECT_DIR / "frontend"

app = FastAPI(title="Quantora QNT30310", version="30310")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

def now_iso():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def load_json(filename: str, fallback):
    p = ARTIFACTS_DIR / filename
    return json.loads(p.read_text()) if p.exists() else fallback

def save_json(filename: str, data):
    (ARTIFACTS_DIR / filename).write_text(json.dumps(data, indent=2))

class AllocationRequest(BaseModel):
    operator_id: str
    requested_capital: float
    allocator_id: str = "allocator_demo_001"
    mandate_name: str = "default_mandate"

class ApprovalRequest(BaseModel):
    allocation_id: str
    approved_capital: float

@app.get("/health")
def health():
    return {"status": "ok", "layer": "QNT30310"}

@app.get("/allocator/deployments")
def deployments():
    return load_json("allocator_deployments.json", {"deployments": []})

@app.get("/allocator/operators")
def operators():
    return load_json("operator_registry.json", {"operators": []})

@app.post("/allocator/request-capital")
def request_capital(payload: AllocationRequest):
    data = load_json("allocator_deployments.json", {"deployments": []})
    item = {
        "allocation_id": f"alloc_{uuid.uuid4().hex[:10]}",
        "allocator_id": payload.allocator_id,
        "operator_id": payload.operator_id,
        "requested_capital": payload.requested_capital,
        "approved_capital": 0,
        "status": "REQUESTED",
        "mandate_name": payload.mandate_name,
        "created_at": now_iso(),
    }
    data["deployments"].append(item)
    save_json("allocator_deployments.json", data)
    return {"status": "requested", "deployment": item}

@app.post("/allocator/approve-capital")
def approve_capital(payload: ApprovalRequest):
    data = load_json("allocator_deployments.json", {"deployments": []})
    found = None
    for d in data["deployments"]:
        if d["allocation_id"] == payload.allocation_id:
            d["approved_capital"] = payload.approved_capital
            d["status"] = "APPROVED"
            d["approved_at"] = now_iso()
            found = d
            break
    save_json("allocator_deployments.json", data)
    if not found:
        return JSONResponse({"error": "allocation not found"}, status_code=404)

    capital_state = load_json("capital_deployment_state.json", {"capital_states": []})
    updated = False
    for s in capital_state["capital_states"]:
        if s["operator_id"] == found["operator_id"]:
            s["deployed_capital"] = payload.approved_capital
            s["allocation_id"] = found["allocation_id"]
            s["allocator_id"] = found["allocator_id"]
            s["status"] = "LIVE_APPROVED"
            s["updated_at"] = now_iso()
            updated = True
            break
    if not updated:
        capital_state["capital_states"].append({
            "operator_id": found["operator_id"],
            "allocation_id": found["allocation_id"],
            "allocator_id": found["allocator_id"],
            "deployed_capital": payload.approved_capital,
            "status": "LIVE_APPROVED",
            "updated_at": now_iso()
        })
    save_json("capital_deployment_state.json", capital_state)

    packet = load_json("allocator_packets.json", {"packets": []})
    packet["packets"].append({
        "packet_id": f"packet_{uuid.uuid4().hex[:8]}",
        "allocation_id": found["allocation_id"],
        "operator_id": found["operator_id"],
        "approved_capital": payload.approved_capital,
        "generated_at": now_iso(),
        "artifacts": ["deployment_record", "capital_state"]
    })
    save_json("allocator_packets.json", packet)

    return {"status": "approved", "deployment": found}

@app.get("/allocator/capital-state")
def capital_state():
    return load_json("capital_deployment_state.json", {"capital_states": []})

@app.get("/allocator/packets")
def packets():
    return load_json("allocator_packets.json", {"packets": []})

@app.get("/")
def root():
    idx = FRONTEND_DIR / "index.html"
    if idx.exists():
        return FileResponse(idx)
    return {"ok": True}

@app.get("/{p}")
def pages(p:str):
    f = FRONTEND_DIR/(p if p.endswith(".html") else p+".html")
    if f.exists():
        return FileResponse(f)
    return JSONResponse({"error":"not found"}, status_code=404)
