from __future__ import annotations

from pathlib import Path
import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.data_loader import load_json

app = FastAPI(title="Quantora QNT30100 Real Data + Trust Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE = Path(__file__).resolve().parents[2]
FRONTEND = BASE / "frontend"
BACKEND_ART = BASE / "backend" / "artifacts"
ART = BASE / "artifacts"


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


def read_root_artifact(name: str):
    path = ART / name
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


@app.get("/")
def root_page():
    return safe_file_response("index.html")


@app.get("/index.html")
def index_page():
    return safe_file_response("index.html")


@app.get("/passport.html")
def passport_page():
    return safe_file_response("passport.html")


@app.get("/audit.html")
def audit_page():
    return safe_file_response("audit.html")


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
    return {"status": "ok", "layer": "QNT30100"}


@app.get("/passport/current")
def passport_current():
    return load_json("passport.json")


@app.get("/passport/score")
def passport_score():
    return load_json("passport_score.json")


@app.get("/passport/violations")
def passport_violations():
    return load_json("violation_registry.json")


@app.get("/audit/current")
def audit_current():
    return load_json("audit_report.json")


@app.get("/system/trust-summary")
def trust_summary():
    passport = load_json("passport.json")
    violations = load_json("violation_registry.json")
    audit = load_json("audit_report.json")
    return {
        "status": "ok",
        "layer": "QNT30100",
        "operator_id": passport.get("operator_id", "operator_demo_001"),
        "trust_score": passport.get("trust_score", 82),
        "audit_status": audit.get("status", "UNKNOWN"),
        "violation_count": violations.get("violation_count", 0),
        "deployment_stage": passport.get("deployment_stage", "STAGE_2_MICRO_LIVE"),
        "passport_status": passport.get("passport_status", "ACTIVE"),
    }


@app.get("/reporting/policy")
def policy():
    path = BASE / "backend" / "institutional_reporting" / "reporting_policy.json"
    return json.loads(path.read_text(encoding="utf-8"))


@app.post("/reporting/generate")
def generate():
    data = read_root_artifact("allocator_reports.json")
    return {"status": "generated", "reports": len(data.get("reports", []))}


@app.get("/reporting/current")
def current():
    return read_root_artifact("allocator_reports.json")


@app.get("/reporting/distribution-log")
def distribution_log():
    return read_root_artifact("distribution_log.json")


@app.get("/reporting/allocator-packets")
def packets():
    return read_root_artifact("allocator_packets.json")


@app.post("/reporting/distribute")
def distribute():
    data = read_root_artifact("distribution_log.json")
    return JSONResponse({"status": "queued", "distributions": len(data.get("events", []))})
