"""Pydantic models for the countdown service."""
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field, HttpUrl


class CountdownRequest(BaseModel):
    """Model describing a countdown generation request."""

    target_datetime: datetime = Field(..., description="Target date and time for the countdown")
    timezone: Optional[str] = Field(
        None, description="IANA timezone string for interpreting the target datetime"
    )
    style: Literal["digital", "minimal"] = Field(
        "digital", description="Presentation style for the generated asset"
    )
    asset_format: Literal["png", "gif"] = Field(
        "png", description="Image format for the generated asset"
    )
    alt_text: Optional[str] = Field(
        "Countdown",
        description="Accessible text applied to the generated image",
        max_length=140,
    )
    click_through_url: Optional[HttpUrl] = Field(
        None,
        description="Optional link that wraps the image inside the embed snippet",
    )


class CountdownResponse(BaseModel):
    """Response metadata returned after generating an asset."""

    expires_at: datetime
    cached: bool
    asset_data_uri: str
    embed_html: str


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = "ok"
    cache_items: int = Field(0, description="Number of live entries in the TTL cache")
    cache_ttl_seconds: int = Field(
        0, description="Configured TTL (seconds) for the in-memory cache"
    )
