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


def build_brand_media_package(
    media_assets: Iterable[Dict],
    distribution_channels: Iterable[Dict],
    campaigns: Iterable[Dict],
    press_hits: Iterable[Dict],
) -> Dict:
    media_assets = list(media_assets or [])
    distribution_channels = list(distribution_channels or [])
    campaigns = list(campaigns or [])
    press_hits = list(press_hits or [])

    active_assets = [x for x in media_assets if (x.get("status") or "").lower() in {"active", "published", "live"}]
    active_channels = [x for x in distribution_channels if (x.get("status") or "").lower() in {"active", "enabled", "live"}]
    running_campaigns = [x for x in campaigns if (x.get("status") or "").lower() in {"active", "running", "live"}]
    published_hits = [x for x in press_hits if (x.get("status") or "").lower() in {"published", "live", "secured"}]

    total_reach = sum(_as_float(x.get("estimated_reach")) for x in campaigns)
    total_press_value = sum(_as_float(x.get("estimated_value")) for x in press_hits)

    asset_rows: List[Dict] = []
    for row in media_assets:
        asset_rows.append({
            "asset_id": row.get("id"),
            "asset_name": row.get("asset_name") or "Media Asset",
            "asset_type": row.get("asset_type") or "article",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    channel_rows: List[Dict] = []
    for row in distribution_channels:
        channel_rows.append({
            "channel_id": row.get("id"),
            "channel_name": row.get("channel_name") or "Channel",
            "channel_type": row.get("channel_type") or "social",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    campaign_rows: List[Dict] = []
    for row in campaigns:
        campaign_rows.append({
            "campaign_id": row.get("id"),
            "campaign_name": row.get("campaign_name") or "Campaign",
            "objective": row.get("objective") or "authority",
            "estimated_reach": _round(_as_float(row.get("estimated_reach"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    press_rows: List[Dict] = []
    for row in press_hits:
        press_rows.append({
            "press_id": row.get("id"),
            "publication_name": row.get("publication_name") or "Publication",
            "headline": row.get("headline") or "Headline",
            "estimated_value": _round(_as_float(row.get("estimated_value"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    brand_score = max(
        45,
        min(
            100,
            int(
                58
                + len(active_assets) * 2
                + len(active_channels) * 2
                + len(running_campaigns) * 3
                + len(published_hits) * 4
            )
        ),
    )

    return {
        "summary": {
            "media_assets_total": len(media_assets),
            "media_assets_active": len(active_assets),
            "channels_total": len(distribution_channels),
            "channels_active": len(active_channels),
            "campaigns_total": len(campaigns),
            "campaigns_running": len(running_campaigns),
            "press_hits_total": len(press_hits),
            "press_hits_published": len(published_hits),
            "estimated_reach_total": _round(total_reach),
            "press_value_total": _round(total_press_value),
            "brand_score": brand_score,
        },
        "media_assets": asset_rows,
        "distribution_channels": channel_rows,
        "campaigns": campaign_rows,
        "press_hits": press_rows,
        "brand_health": {
            "asset_registry_ready": bool(media_assets),
            "channel_registry_ready": bool(distribution_channels),
            "campaign_registry_ready": bool(campaigns),
            "press_registry_ready": bool(press_hits),
            "brand_score": brand_score,
        },
    }
