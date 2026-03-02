"""
TikTok platform configuration.
TikTok can download videos without watermark.
"""

from .base import BasePlatformConfig


class TikTokConfig(BasePlatformConfig):
    platform_name = "tiktok"
    display_name = "TikTok"
    requires_cookies = False  # Often works without
    has_separate_streams = False
    cookie_filename = "tiktok_cookies.txt"
    
    def get_yt_dlp_config(self, user_agent):
        return {
            "http_headers": {
                "User-Agent": user_agent,
                "Referer": "https://www.tiktok.com/",
            },
            "socket_timeout": 30,
            "retries": 8,
            "extractor_retries": 8,
            "fragment_retries": 8,
        }
    
    def get_format_selector(self):
        # Prefer no watermark version
        return "best"
