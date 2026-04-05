"""
Platform API Loader
Automatically loads all platform configurations and provides easy access.
"""

import os
from .base import BasePlatformConfig
from .youtube import YouTubeConfig
from .instagram import InstagramConfig
from .facebook import FacebookConfig
from .tiktok import TikTokConfig
from .twitter import TwitterConfig
from .reddit import RedditConfig
from .vimeo import VimeoConfig
from .dailymotion import DailymotionConfig
from .twitch import TwitchConfig
from .streamable import StreamableConfig


# Platform registry - maps platform names to config classes
PLATFORM_CONFIGS = {
    "youtube": YouTubeConfig(),
    "instagram": InstagramConfig(),
    "facebook": FacebookConfig(),
    "tiktok": TikTokConfig(),
    "x": TwitterConfig(),  # Twitter/X
    "twitter": TwitterConfig(),  # Alias
    "reddit": RedditConfig(),
    "vimeo": VimeoConfig(),
    "dailymotion": DailymotionConfig(),
    "twitch": TwitchConfig(),
    "streamable": StreamableConfig(),
}


def get_platform_config(platform_name):
    """
    Get configuration for a specific platform.
    
    Args:
        platform_name: Platform identifier (e.g., "instagram", "youtube")
        
    Returns:
        BasePlatformConfig: Platform-specific config or generic fallback
    """
    # Return specific config if available, else generic
    return PLATFORM_CONFIGS.get(platform_name.lower(), BasePlatformConfig())


def get_all_platforms():
    """
    Get list of all supported platform names.
    
    Returns:
        list: Platform names with optimized configs
    """
    return sorted(set(PLATFORM_CONFIGS.keys()))


def get_platforms_requiring_cookies():
    """
    Get list of platforms that require/recommend cookies.
    
    Returns:
        list: Platform names that need cookies
    """
    return [
        name for name, config in PLATFORM_CONFIGS.items()
        if config.requires_cookies
    ]


def get_cookie_file_path(platform_name):
    """
    Get the expected cookie file path for a platform.

    Args:
        platform_name: Platform identifier

    Returns:
        str: Path to cookie file or None if not found
    """
    try:
        import app_settings
        base = app_settings.get_data_dir()
    except Exception:
        try:
            from android.storage import primary_external_storage_path
            base = os.path.join(primary_external_storage_path(), "Download", "videodownloader")
        except ImportError:
            base = os.path.join(os.path.expanduser("~"), "Downloads", "videodownloader")

    os.makedirs(base, exist_ok=True)
    
    # Try platform-specific cookie file first
    config = get_platform_config(platform_name)
    platform_cookie = os.path.join(base, config.get_cookie_filename())
    if os.path.exists(platform_cookie):
        return platform_cookie
    
    # Fall back to generic cookies.txt
    generic_cookie = os.path.join(base, "cookies.txt")
    if os.path.exists(generic_cookie):
        return generic_cookie
    
    return None


# Convenience exports
__all__ = [
    'BasePlatformConfig',
    'get_platform_config',
    'get_all_platforms',
    'get_platforms_requiring_cookies',
    'get_cookie_file_path',
    'PLATFORM_CONFIGS',
]
