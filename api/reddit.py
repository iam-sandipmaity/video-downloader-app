"""
Reddit platform configuration.
"""

from .base import BasePlatformConfig


class RedditConfig(BasePlatformConfig):
    platform_name = "reddit"
    display_name = "Reddit"
    requires_cookies = False
    has_separate_streams = False
    
    def get_yt_dlp_config(self, user_agent):
        return {
            "http_headers": {
                "User-Agent": user_agent,
            },
            "socket_timeout": 30,
            "retries": 5,
            "extractor_retries": 5,
        }
    
    def get_format_selector(self):
        return "best"
