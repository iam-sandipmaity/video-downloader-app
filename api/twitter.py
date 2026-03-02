"""
Twitter/X platform configuration.
"""

from .base import BasePlatformConfig


class TwitterConfig(BasePlatformConfig):
    platform_name = "x"  # Platform identifier
    display_name = "Twitter/X"
    requires_cookies = False
    has_separate_streams = False
    cookie_filename = "x_cookies.txt"
    
    def get_yt_dlp_config(self, user_agent):
        return {
            "http_headers": {
                "User-Agent": user_agent,
            },
            "socket_timeout": 30,
            "retries": 5,
            "extractor_retries": 5,
            "fragment_retries": 5,
        }
    
    def get_format_selector(self):
        return "best"
