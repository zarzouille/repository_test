"""FastAPI application entrypoint for the countdown service."""
from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass
from datetime import timedelta

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from zoneinfo import ZoneInfo

from .config import get_settings
from .models import CountdownRequest, CountdownResponse, HealthResponse
from .utils.asset_generator import generate_asset
from .utils.cache import TTLCache
from .utils.template_renderer import render_embed_snippet
from .utils.time_utils import coerce_timezone, get_time_remaining

settings = get_settings()
app = FastAPI(title=settings.app_name)
cache = TTLCache(ttl_seconds=settings.cache_ttl_seconds)


@dataclass
class RequestContext:
    timezone: ZoneInfo
    delta: timedelta
    cache_key: str


def _request_context(payload: CountdownRequest) -> RequestContext:
    tz = coerce_timezone(payload.timezone or settings.default_timezone)
    delta, normalized_target = get_time_remaining(payload.target_datetime, tz)
    payload_str = f"{normalized_target.isoformat()}|{tz.key}|{payload.style}|{payload.asset_format}"
    cache_key = hashlib.sha256(payload_str.encode()).hexdigest()
    return RequestContext(
        timezone=tz,
        delta=delta,
        cache_key=cache_key,
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    stats = cache.stats()
    return HealthResponse(cache_items=stats.items, cache_ttl_seconds=stats.ttl_seconds)


@app.post("/countdown/asset")
def countdown_asset(request: CountdownRequest):
    try:
        context = _request_context(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    def factory():
        return generate_asset(context.delta, request.style, request.asset_format)

    asset_bytes, entry, cached = cache.get_or_set(context.cache_key, factory)
    media_type = "image/gif" if request.asset_format == "gif" else "image/png"
    headers = {"X-Cache": "HIT" if cached else "MISS", "X-Expires-At": entry.expires_at.isoformat()}
    return Response(content=asset_bytes, media_type=media_type, headers=headers)


@app.post("/countdown/embed", response_model=CountdownResponse)
def countdown_embed(request: CountdownRequest) -> CountdownResponse:
    try:
        context = _request_context(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    asset_bytes, entry, cached = cache.get_or_set(
        context.cache_key,
        lambda: generate_asset(context.delta, request.style, request.asset_format),
    )

    b64 = base64.b64encode(asset_bytes).decode()
    asset_url = f"data:image/{request.asset_format};base64,{b64}"
    snippet = render_embed_snippet(
        asset_url,
        alt_text=request.alt_text or "Countdown",
        link_url=str(request.click_through_url) if request.click_through_url else None,
    )
    return CountdownResponse(
        expires_at=entry.expires_at,
        cached=cached,
        asset_data_uri=asset_url,
        embed_html=snippet,
    )


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"message": "Countdown service is running", "docs": "/docs"}


def _resolve_port() -> int:
    try:
        return int(os.environ.get("PORT", "8000"))
    except ValueError:
        return 8000


if __name__ == "__main__":
    uvicorn.run(app, host=os.environ.get("HOST", "0.0.0.0"), port=_resolve_port())
