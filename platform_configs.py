"""
Platform-specific configurations for yt-dlp.
Each platform may have unique requirements for authentication, cookies, headers, etc.
"""

import os


def get_platform_config(platform, user_agent):
    """
    Returns platform-specific yt-dlp configuration.
    
    Args:
        platform: Platform name (instagram, facebook, x, tiktok, etc.)
        user_agent: User agent string to use
        
    Returns:
        dict: Additional configuration options for yt-dlp
    """
    configs = {
        "instagram": {
            "http_headers": {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-us,en;q=0.5",
                "Sec-Fetch-Mode": "navigate",
            },
            # Instagram often provides combined video+audio, prefer those
            "format": "best[vcodec][acodec]/best",
            # Increase retries for Instagram due to rate limiting
            "extractor_retries": 10,
            "retries": 15,
            "fragment_retries": 15,
        },
        
        "facebook": {
            "http_headers": {
                "User-Agent": user_agent,
            },
            "format": "best[vcodec][acodec]/best",
            "extractor_retries": 8,
            "retries": 12,
        },
        
        "x": {  # Twitter/X
            "http_headers": {
                "User-Agent": user_agent,
            },
            "format": "best[vcodec][acodec]/best",
            "extractor_retries": 5,
        },
        
        "tiktok": {
            "http_headers": {
                "User-Agent": user_agent,
                "Referer": "https://www.tiktok.com/",
            },
            "format": "best[vcodec][acodec]/best",
            "extractor_retries": 8,
        },
        
        "reddit": {
            "http_headers": {
                "User-Agent": user_agent,
            },
            "format": "best[vcodec][acodec]/best",
        },
        
        "vimeo": {
            "http_headers": {
                "User-Agent": user_agent,
            },
            "format": "best[vcodec][acodec]/best",
        },
        
        "dailymotion": {
            "http_headers": {
                "User-Agent": user_agent,
            },
            "format": "best[vcodec][acodec]/best",
        },
        
        "twitch": {
            "http_headers": {
                "User-Agent": user_agent,
            },
            "format": "best[vcodec][acodec]/best",
        },
        
        "streamable": {
            "http_headers": {
                "User-Agent": user_agent,
            },
            "format": "best[vcodec][acodec]/best",
        },
        
        "pinterest": {
            "http_headers": {
                "User-Agent": user_agent,
            },
            "format": "best[vcodec][acodec]/best",
        },
        
        "linkedin": {
            "http_headers": {
                "User-Agent": user_agent,
            },
            "format": "best[vcodec][acodec]/best",
        },
    }
    
    return configs.get(platform, {})


def needs_cookies(platform):
    """
    Returns True if platform typically requires cookies for reliable access.
    """
    return platform in ["instagram", "facebook", "x"]


def get_cookie_file(platform):
    """
    Returns path to cookies file if it exists, None otherwise.
    """
    try:
        from android.storage import primary_external_storage_path
        base = os.path.join(primary_external_storage_path(), "Download", "videodownloader")
    except ImportError:
        base = os.path.join(os.path.expanduser("~"), "Downloads", "videodownloader")
    
    os.makedirs(base, exist_ok=True)
    cookie_file = os.path.join(base, f"{platform}_cookies.txt")
    
    if os.path.exists(cookie_file):
        return cookie_file
    
    # Also check for generic cookies.txt
    generic_cookies = os.path.join(base, "cookies.txt")
    if os.path.exists(generic_cookies):
        return generic_cookies
    
    return None


def supports_separate_streams(platform):
    """
    Returns True if platform typically provides separate video/audio streams.
    YouTube-like behavior.
    """
    # Most platforms provide combined streams, not separate like YouTube
    return platform in ["youtube", "vimeo", "dailymotion"]
