from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent
ARTIFACTS_DIR = BACKEND_DIR / "artifacts"
FRONTEND_DIR = PROJECT_DIR / "frontend"

app = FastAPI(title="Quantora QNT30200", version="30200")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_json(filename: str, fallback):
    path = ARTIFACTS_DIR / filename
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return fallback

@app.get("/health")
def health():
    return {"status": "ok", "layer": "QNT30200"}

@app.get("/passport/current")
def passport_current():
    return load_json("passport.json", {})

@app.get("/passport/score")
def passport_score():
    return load_json("passport_score.json", {})

@app.get("/passport/violations")
def passport_violations():
    return load_json("violation_registry.json", {})

@app.get("/audit/current")
def audit_current():
    return load_json("audit_report.json", {})

@app.get("/system/trust-summary")
def trust_summary():
    passport = load_json("passport.json", {})
    score = load_json("passport_score.json", {})
    audit = load_json("audit_report.json", {})
    violations = load_json("violation_registry.json", {})
    return {
        "status": "ok",
        "layer": "QNT30200",
        "operator_id": passport.get("operator_id", "operator_demo_001"),
        "trust_score": score.get("trust_score", passport.get("trust_score", 0)),
        "audit_status": audit.get("status", "UNKNOWN"),
        "violation_count": violations.get("violation_count", 0),
        "deployment_stage": passport.get("deployment_stage", "STAGE_0_BLOCKED"),
        "passport_status": passport.get("passport_status", "UNKNOWN"),
    }

@app.get("/allocator/profile")
def allocator_profile():
    return load_json("allocator_profile.json", {})

@app.get("/allocator/report")
def allocator_report():
    return load_json("allocator_report.json", {})

@app.post("/allocator/request-access")
def allocator_request_access():
    return {
        "status": "accepted",
        "layer": "QNT30200",
        "request_id": "alloc_req_demo_001",
        "message": "Allocator access request recorded."
    }

@app.get("/")
def root():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse({"status": "ok", "message": "Quantora backend live", "docs": "/docs", "health": "/health"})

@app.get("/{page_name}")
def static_pages(page_name: str):
    page = FRONTEND_DIR / page_name
    if page.suffix == "" and not page_name.endswith(".html"):
        page = FRONTEND_DIR / f"{page_name}.html"
    if page.exists() and page.is_file():
        return FileResponse(page)
    return JSONResponse({"error": "not found", "page": page_name}, status_code=404)
