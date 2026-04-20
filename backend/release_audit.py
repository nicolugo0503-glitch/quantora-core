from pathlib import Path
import json

EXPECTED_PANELS = [
    "automation_loop_panel.html",
    "ai_decision_panel.html",
    "multi_strategy_panel.html",
    "execution_optimization_panel.html",
    "governance_system_panel.html",
    "autonomy_control_plane_panel.html",
    "broker_abstraction_panel.html",
    "venue_adapter_framework_panel.html",
    "real_venue_connectors_panel.html",
    "portfolio_risk_fabric_panel.html",
    "allocator_intelligence_panel.html",
    "performance_intelligence_panel.html",
    "research_memory_panel.html",
    "scenario_engine_panel.html",
    "policy_simulator_panel.html",
    "institutional_portfolio_brain_panel.html",
    "operator_command_mesh_panel.html",
    "capital_committee_engine_panel.html",
    "strategy_factory_panel.html",
]

EXPECTED_ENDPOINT_MARKERS = [
    "/strategy-factory/status",
    "/capital-committee/status",
    "/command-mesh/status",
    "/policy-simulator/status",
    "/portfolio-brain/status",
]

STALE_MARKERS = [
    "QNT30332",
    "QNT30359",
    "Scenario Engine + Stress Testing Fabric",
    "Multi Strategy System",
]


def build_release_audit(project_dir: Path):
    backend_main = project_dir / "backend" / "app" / "main.py"
    frontend_index = project_dir / "frontend" / "index.html"
    frontend_dir = project_dir / "frontend"

    main_text = backend_main.read_text(encoding="utf-8", errors="ignore") if backend_main.exists() else ""
    index_text = frontend_index.read_text(encoding="utf-8", errors="ignore") if frontend_index.exists() else ""

    endpoints = {marker: (marker in main_text) for marker in EXPECTED_ENDPOINT_MARKERS}
    panels = {panel: (frontend_dir / panel).exists() for panel in EXPECTED_PANELS}
    stale_main = [marker for marker in STALE_MARKERS if marker in main_text]
    stale_index = [marker for marker in STALE_MARKERS if marker in index_text]

    return {
        "release": {
            "release_id": "QNT30366",
            "release_name": "release normalization + deployment audit fix",
            "status": "normalized" if not stale_main and not stale_index else "mixed",
        },
        "backend": {
            "main_exists": backend_main.exists(),
            "expected_endpoints_present": endpoints,
        },
        "frontend": {
            "index_exists": frontend_index.exists(),
            "expected_panels_present": panels,
        },
        "stale_markers": {
            "backend_main": stale_main,
            "frontend_index": stale_index,
        },
        "summary": {
            "endpoint_coverage_pct": round((sum(1 for v in endpoints.values() if v) / max(len(endpoints), 1)) * 100.0, 2),
            "panel_coverage_pct": round((sum(1 for v in panels.values() if v) / max(len(panels), 1)) * 100.0, 2),
            "stale_marker_count": len(stale_main) + len(stale_index),
        },
    }
