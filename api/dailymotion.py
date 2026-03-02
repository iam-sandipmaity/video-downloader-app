"""
Dailymotion platform configuration.
"""

from .base import BasePlatformConfig


class DailymotionConfig(BasePlatformConfig):
    platform_name = "dailymotion"
    display_name = "Dailymotion"
    requires_cookies = False
    has_separate_streams = True
    
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
