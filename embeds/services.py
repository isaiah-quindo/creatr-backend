"""URL detection + oEmbed fetching for video portfolio items.

TikTok and YouTube expose free, unauthenticated oEmbed endpoints. Instagram's
oEmbed requires a Meta app token, so for the MVP we just store the URL and
render a placeholder on the public page.
"""

from __future__ import annotations

import re
from typing import Optional

import requests


OEMBED_ENDPOINTS = {
    "tiktok": "https://www.tiktok.com/oembed?url={url}",
    "youtube": "https://www.youtube.com/oembed?url={url}&format=json",
}

_PLATFORM_PATTERNS = {
    "tiktok": re.compile(
        r"(tiktok\.com/@[\w.\-]+/video/\d+|vm\.tiktok\.com/\w+|tiktok\.com/t/\w+)",
        re.IGNORECASE,
    ),
    "youtube": re.compile(
        r"(youtube\.com/watch\?v=[\w\-]+|youtu\.be/[\w\-]+|youtube\.com/shorts/[\w\-]+)",
        re.IGNORECASE,
    ),
    "instagram": re.compile(
        r"(instagram\.com/(p|reel|reels|tv)/[\w\-]+)",
        re.IGNORECASE,
    ),
}


def detect_platform(url: str) -> Optional[str]:
    if not url:
        return None
    for platform, pattern in _PLATFORM_PATTERNS.items():
        if pattern.search(url):
            return platform
    return None


def fetch_embed_data(url: str) -> dict:
    """Return a dict shaped like a PortfolioItem's embed fields.

    Keys: platform, original_url, thumbnail_url, video_title, embed_html.
    Always returns a dict — on failure, fields are empty strings so the caller
    can still persist the URL.
    """
    platform = detect_platform(url)
    result = {
        "platform": platform or "",
        "original_url": url,
        "thumbnail_url": "",
        "video_title": "",
        "embed_html": "",
    }
    if not platform:
        return result

    if platform in OEMBED_ENDPOINTS:
        try:
            resp = requests.get(
                OEMBED_ENDPOINTS[platform].format(url=url),
                timeout=5,
                headers={"User-Agent": "creatr-embed/1.0"},
            )
            if resp.ok:
                data = resp.json()
                result["thumbnail_url"] = data.get("thumbnail_url", "") or ""
                result["video_title"] = data.get("title", "") or ""
                result["embed_html"] = data.get("html", "") or ""
        except (requests.RequestException, ValueError):
            pass  # graceful fallback — caller still has the URL + platform

    elif platform == "instagram":
        # Instagram oEmbed needs a Meta access token; defer to post-MVP.
        result["video_title"] = "Instagram post"

    return result
