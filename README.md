# Countdown Asset Service

This repository contains a lightweight FastAPI web service that generates countdown assets
(PNG or GIF images) suitable for embedding into email campaigns. Clients can call REST
endpoints to request countdowns that respect a target datetime, timezone, and visual style.

## Features

- **Dynamic asset generation** using Pillow with configurable presentation styles.
- **Embeddable HTML snippets** returned as JSON for quick integration.
- **In-memory TTL caching** to avoid regenerating identical assets.
- **Utility modules** for time calculations, HTML template rendering, and caching.

## Project Structure

```
src/
  countdown_service/
    main.py            # FastAPI application with /countdown endpoints
    config.py          # Environment-driven configuration
    models.py          # Pydantic request/response schemas
    utils/
      asset_generator.py
      cache.py
      template_renderer.py
      time_utils.py
requirements.txt
```

## Running the Service

1. Create and activate a virtual environment (optional but recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Launch the FastAPI application with Uvicorn:
   ```bash
   uvicorn countdown_service.main:app --reload
   ```
4. Visit [http://localhost:8000/docs](http://localhost:8000/docs) for interactive OpenAPI
   documentation and [http://localhost:8000/health](http://localhost:8000/health) to
   inspect the cache (item count plus TTL).

## Example Usage

Request a PNG asset via the `/countdown/asset` endpoint:

```bash
curl -X POST http://localhost:8000/countdown/asset \
  -H "Content-Type: application/json" \
  -d '{
        "target_datetime": "2024-12-31T23:59:59",
        "timezone": "UTC",
        "style": "digital",
        "asset_format": "png"
      }' --output countdown.png
```

Request an embeddable snippet (base64 data URI) via `/countdown/embed`. The payload can
optionally include `alt_text` and a `click_through_url` that wraps the image in a link:

```bash
curl -X POST http://localhost:8000/countdown/embed \
  -H "Content-Type: application/json" \
  -d '{
        "target_datetime": "2024-12-31T23:59:59",
        "timezone": "America/New_York",
        "style": "minimal",
        "asset_format": "gif",
        "alt_text": "Q4 Countdown",
        "click_through_url": "https://example.com/promo"
      }'
```

The embed endpoint returns JSON that includes the data URI (`asset_data_uri`), the
rendered `embed_html`, `expires_at`, and a `cached` flag describing whether the asset
was served from cache.

## Configuration

Environment variables prefixed with `COUNTDOWN_` adjust runtime behavior:

- `COUNTDOWN_APP_NAME` – override the FastAPI application title.
- `COUNTDOWN_DEFAULT_TIMEZONE` – timezone used when requests omit one (defaults to `UTC`).
- `COUNTDOWN_CACHE_TTL_SECONDS` – TTL for the in-memory cache (defaults to `60`).

## Notes

- The generated GIFs are single-frame images for compatibility across email clients.
- Production deployments should consider a persistent cache or CDN and hardened error
  handling.
