from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import json

app = FastAPI(title="Quantora QNT30000 Deploy Ready")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://[::1]:5173",
        "http://127.0.0.1:8010",
        "http://localhost:8010",
        "null",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE = Path(__file__).resolve().parents[2]
ART = BASE / "artifacts"
FRONTEND = BASE / "frontend"

def read_json(name: str):
    path = ART / name
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}

def safe_file_response(filename: str, media_type: str | None = None):
    path = FRONTEND / filename
    if path.exists():
        return FileResponse(path, media_type=media_type)
    return JSONResponse(
        {
            "status": "ok",
            "message": "Quantora backend live",
            "missing_file": filename,
            "docs": "/docs",
            "health": "/health",
        }
    )

@app.get("/")
def root_page():
    return safe_file_response("index.html")

@app.get("/index.html")
def index_page():
    return safe_file_response("index.html")

@app.get("/reporting.html")
def reporting_page():
    return safe_file_response("reporting.html")

@app.get("/distribution.html")
def distribution_page():
    return safe_file_response("distribution.html")

@app.get("/config.js")
def config_js():
    return safe_file_response("config.js", media_type="application/javascript")

@app.get("/health")
def health():
    return {"status": "ok", "layer": "QNT30000"}

@app.get("/reporting/policy")
def policy():
    path = BASE / "backend" / "institutional_reporting" / "reporting_policy.json"
    return json.loads(path.read_text(encoding="utf-8"))

@app.post("/reporting/generate")
def generate():
    data = read_json("allocator_reports.json")
    return {"status": "generated", "reports": len(data.get("reports", []))}

@app.get("/reporting/current")
def current():
    return read_json("allocator_reports.json")

@app.get("/reporting/distribution-log")
def distribution_log():
    return read_json("distribution_log.json")

@app.get("/reporting/allocator-packets")
def packets():
    return read_json("allocator_packets.json")

@app.post("/reporting/distribute")
def distribute():
    data = read_json("distribution_log.json")
    return JSONResponse({"status": "queued", "distributions": len(data.get("events", []))})
