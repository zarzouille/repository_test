"""Simple template rendering utilities."""
from __future__ import annotations

from string import Template


def render_embed_snippet(
    asset_url: str, *, alt_text: str = "Countdown", link_url: str | None = None
) -> str:
    """Render a minimal HTML snippet for embedding the countdown asset."""

    image_markup = Template(
        "<img src=\"$url\" alt=\"$alt\" style=\"max-width:100%; height:auto;\" />"
    ).substitute(url=asset_url, alt=alt_text)

    if link_url:
        wrapped_markup = Template(
            "<a href=\"$href\" target=\"_blank\" rel=\"noopener noreferrer\">$body</a>"
        ).substitute(href=link_url, body=image_markup)
    else:
        wrapped_markup = image_markup

    snippet = Template(
        """
        <div style="text-align:center">
            $body
        </div>
        """
    )
    return snippet.substitute(body=wrapped_markup)
