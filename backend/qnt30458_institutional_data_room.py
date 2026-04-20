from __future__ import annotations

from typing import Dict, Iterable, List


def _as_float(value, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def build_data_room_package(
    folders: Iterable[Dict],
    documents: Iterable[Dict],
    access_grants: Iterable[Dict],
    allocator_sessions: Iterable[Dict],
) -> Dict:
    folders = list(folders or [])
    documents = list(documents or [])
    access_grants = list(access_grants or [])
    allocator_sessions = list(allocator_sessions or [])

    active_folders = [f for f in folders if (f.get("status") or "").lower() in {"active", "published", "live"}]
    published_docs = [d for d in documents if (d.get("status") or "").lower() in {"published", "approved", "live"}]
    active_grants = [g for g in access_grants if (g.get("status") or "").lower() in {"active", "granted", "enabled"}]
    active_sessions = [s for s in allocator_sessions if (s.get("status") or "").lower() in {"active", "open"}]

    folder_rows: List[Dict] = []
    for row in folders:
        folder_rows.append({
            "folder_id": row.get("id"),
            "folder_name": row.get("folder_name") or "Data Room Folder",
            "folder_type": row.get("folder_type") or "general",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    doc_rows: List[Dict] = []
    for row in documents:
        doc_rows.append({
            "document_id": row.get("id"),
            "document_name": row.get("document_name") or "Document",
            "folder_name": row.get("folder_name") or "General",
            "document_type": row.get("document_type") or "pdf",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    grant_rows: List[Dict] = []
    for row in access_grants:
        grant_rows.append({
            "grant_id": row.get("id"),
            "allocator_name": row.get("allocator_name") or "Allocator",
            "access_scope": row.get("access_scope") or "standard",
            "status": row.get("status") or "pending",
            "expires_at": row.get("expires_at"),
            "created_at": row.get("created_at"),
        })

    session_rows: List[Dict] = []
    for row in allocator_sessions:
        session_rows.append({
            "session_id": row.get("id"),
            "allocator_name": row.get("allocator_name") or "Allocator",
            "last_document": row.get("last_document") or "-",
            "status": row.get("status") or "inactive",
            "created_at": row.get("created_at"),
        })

    room_score = max(
        45,
        min(
            100,
            int(
                55
                + len(active_folders) * 3
                + len(published_docs)
                + len(active_grants) * 3
                + len(active_sessions) * 2
            )
        ),
    )

    return {
        "summary": {
            "folders_total": len(folders),
            "folders_active": len(active_folders),
            "documents_total": len(documents),
            "documents_published": len(published_docs),
            "access_grants_active": len(active_grants),
            "allocator_sessions_active": len(active_sessions),
            "room_score": room_score,
        },
        "folders": folder_rows,
        "documents": doc_rows,
        "access_grants": grant_rows,
        "allocator_sessions": session_rows,
        "room_health": {
            "folder_registry_ready": bool(folders),
            "document_registry_ready": bool(documents),
            "access_control_ready": bool(access_grants),
            "allocator_session_ready": bool(allocator_sessions),
            "room_score": room_score,
        },
    }
