"""
Batch download support — detect and manage multiple URLs.
"""

import re
from urllib.parse import urlparse

# Common URL regex: matches http(s) URLs with common TLDs
_URL_RE = re.compile(
    r'https?://[^\s<>"\'{}|\\^`\[\]]+',
    re.IGNORECASE,
)

_SUPPORTED_DOMAINS = {
    "youtube.com", "youtu.be",
    "instagram.com", "instagr.am",
    "facebook.com", "fb.watch", "fb.me",
    "x.com", "twitter.com",
    "tiktok.com",
    "reddit.com", "redd.it",
    "vimeo.com",
    "dailymotion.com", "dai.ly",
    "twitch.tv",
    "streamable.com",
    "pinterest.com", "pin.it",
    "linkedin.com",
}


def extract_urls(text):
    """Return a list of unique URLs found in *text*."""
    if not text or not isinstance(text, str):
        return []

    candidates = _URL_RE.findall(text)
    seen = set()
    urls = []
    for raw in candidates:
        # Strip trailing punctuation that may have been captured
        url = raw.rstrip(".,;:!?")
        if url not in seen and urlparse(url).scheme in ("http", "https"):
            seen.add(url)
            urls.append(url)
    return urls


def is_supported_platform(url):
    """Return True if the URL's host is in the known supported domain set."""
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    for d in _SUPPORTED_DOMAINS:
        if d in host:
            return True
    return False


def classify_urls(text):
    """Analyse *text* and return a summary dict for UI display.

    Returns:
        {
            "urls":      list of detected URLs,
            "supported": count of supported-platform URLs,
            "unknown":   count of URLs on unsupported hosts,
        }
    """
    urls = extract_urls(text)
    supported = sum(1 for u in urls if is_supported_platform(u))
    return {
        "urls": urls,
        "supported": supported,
        "unknown": max(0, len(urls) - supported),
    }
