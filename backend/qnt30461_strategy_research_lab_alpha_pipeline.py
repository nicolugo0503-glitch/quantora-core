from __future__ import annotations

from typing import Dict, Iterable, List


def _as_float(value, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _round(value: float) -> float:
    return round(float(value), 2)


def build_strategy_research_package(
    hypotheses: Iterable[Dict],
    experiments: Iterable[Dict],
    alpha_candidates: Iterable[Dict],
    validations: Iterable[Dict],
) -> Dict:
    hypotheses = list(hypotheses or [])
    experiments = list(experiments or [])
    alpha_candidates = list(alpha_candidates or [])
    validations = list(validations or [])

    active_hypotheses = [x for x in hypotheses if (x.get("status") or "").lower() in {"active", "researching", "open"}]
    running_experiments = [x for x in experiments if (x.get("status") or "").lower() in {"running", "active", "in_progress"}]
    approved_candidates = [x for x in alpha_candidates if (x.get("status") or "").lower() in {"approved", "promoted", "ready"}]
    passed_validations = [x for x in validations if (x.get("status") or "").lower() in {"passed", "approved", "valid"}]

    hypothesis_rows: List[Dict] = []
    for row in hypotheses:
        hypothesis_rows.append({
            "hypothesis_id": row.get("id"),
            "hypothesis_name": row.get("hypothesis_name") or "Hypothesis",
            "research_domain": row.get("research_domain") or "market_structure",
            "status": row.get("status") or "draft",
            "owner": row.get("owner") or "research",
            "created_at": row.get("created_at"),
        })

    experiment_rows: List[Dict] = []
    for row in experiments:
        experiment_rows.append({
            "experiment_id": row.get("id"),
            "experiment_name": row.get("experiment_name") or "Experiment",
            "dataset_name": row.get("dataset_name") or "internal",
            "status": row.get("status") or "draft",
            "sharpe_estimate": _round(_as_float(row.get("sharpe_estimate"))),
            "created_at": row.get("created_at"),
        })

    alpha_rows: List[Dict] = []
    for row in alpha_candidates:
        alpha_rows.append({
            "candidate_id": row.get("id"),
            "candidate_name": row.get("candidate_name") or "Alpha Candidate",
            "signal_family": row.get("signal_family") or "momentum",
            "status": row.get("status") or "draft",
            "score": _round(_as_float(row.get("score"))),
            "created_at": row.get("created_at"),
        })

    validation_rows: List[Dict] = []
    for row in validations:
        validation_rows.append({
            "validation_id": row.get("id"),
            "validation_name": row.get("validation_name") or "Validation",
            "candidate_name": row.get("candidate_name") or "Candidate",
            "status": row.get("status") or "pending",
            "confidence": _round(_as_float(row.get("confidence"))),
            "created_at": row.get("created_at"),
        })

    lab_score = max(
        45,
        min(
            100,
            int(
                55
                + len(active_hypotheses) * 2
                + len(running_experiments) * 3
                + len(approved_candidates) * 4
                + len(passed_validations) * 2
            )
        ),
    )

    return {
        "summary": {
            "hypotheses_total": len(hypotheses),
            "active_hypotheses": len(active_hypotheses),
            "experiments_total": len(experiments),
            "running_experiments": len(running_experiments),
            "alpha_candidates": len(alpha_candidates),
            "approved_candidates": len(approved_candidates),
            "validations_passed": len(passed_validations),
            "lab_score": lab_score,
        },
        "hypotheses": hypothesis_rows,
        "experiments": experiment_rows,
        "alpha_candidates": alpha_rows,
        "validations": validation_rows,
        "lab_health": {
            "research_registry_ready": bool(hypotheses),
            "experiment_engine_ready": bool(experiments),
            "alpha_pipeline_ready": bool(alpha_candidates),
            "validation_engine_ready": bool(validations),
            "lab_score": lab_score,
        },
    }
