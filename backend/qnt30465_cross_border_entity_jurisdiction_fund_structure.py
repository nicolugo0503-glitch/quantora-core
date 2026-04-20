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


def build_jurisdiction_structure_package(
    entities: Iterable[Dict],
    jurisdictions: Iterable[Dict],
    fund_structures: Iterable[Dict],
    compliance_links: Iterable[Dict],
) -> Dict:
    entities = list(entities or [])
    jurisdictions = list(jurisdictions or [])
    fund_structures = list(fund_structures or [])
    compliance_links = list(compliance_links or [])

    active_entities = [x for x in entities if (x.get("status") or "").lower() in {"active", "live", "formed"}]
    approved_jurisdictions = [x for x in jurisdictions if (x.get("status") or "").lower() in {"approved", "active", "ready"}]
    live_structures = [x for x in fund_structures if (x.get("status") or "").lower() in {"active", "live", "ready"}]
    linked_controls = [x for x in compliance_links if (x.get("status") or "").lower() in {"active", "linked", "enabled"}]

    entity_rows: List[Dict] = []
    for row in entities:
        entity_rows.append({
            "entity_id": row.get("id"),
            "entity_name": row.get("entity_name") or "Entity",
            "entity_type": row.get("entity_type") or "management_company",
            "jurisdiction": row.get("jurisdiction") or "US",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    jurisdiction_rows: List[Dict] = []
    for row in jurisdictions:
        jurisdiction_rows.append({
            "jurisdiction_id": row.get("id"),
            "jurisdiction_name": row.get("jurisdiction_name") or "Jurisdiction",
            "regulatory_profile": row.get("regulatory_profile") or "standard",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    structure_rows: List[Dict] = []
    for row in fund_structures:
        structure_rows.append({
            "structure_id": row.get("id"),
            "structure_name": row.get("structure_name") or "Fund Structure",
            "master_entity": row.get("master_entity") or "Master Fund",
            "feeder_entity": row.get("feeder_entity") or "Feeder Fund",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    control_rows: List[Dict] = []
    for row in compliance_links:
        control_rows.append({
            "link_id": row.get("id"),
            "entity_name": row.get("entity_name") or "Entity",
            "control_name": row.get("control_name") or "Control",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    structure_score = max(
        45,
        min(
            100,
            int(
                60
                + len(active_entities) * 3
                + len(approved_jurisdictions) * 2
                + len(live_structures) * 4
                + len(linked_controls) * 2
            )
        ),
    )

    return {
        "summary": {
            "entities_total": len(entities),
            "entities_active": len(active_entities),
            "jurisdictions_total": len(jurisdictions),
            "jurisdictions_approved": len(approved_jurisdictions),
            "fund_structures": len(fund_structures),
            "fund_structures_live": len(live_structures),
            "compliance_links": len(compliance_links),
            "structure_score": structure_score,
        },
        "entities": entity_rows,
        "jurisdictions": jurisdiction_rows,
        "fund_structures": structure_rows,
        "compliance_links": control_rows,
        "structure_health": {
            "entity_registry_ready": bool(entities),
            "jurisdiction_registry_ready": bool(jurisdictions),
            "structure_registry_ready": bool(fund_structures),
            "control_linking_ready": bool(compliance_links),
            "structure_score": structure_score,
        },
    }
