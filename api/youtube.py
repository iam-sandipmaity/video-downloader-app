"""
YouTube platform configuration.
Note: YouTube uses custom downloader.py with specialized muxing.
This config is mainly for reference - actual YouTube downloads go through downloader.py
"""

from .base import BasePlatformConfig


class YouTubeConfig(BasePlatformConfig):
    platform_name = "youtube"
    display_name = "YouTube"
    requires_cookies = False  # Works without cookies
    has_separate_streams = True  # Provides separate video/audio
    
    def get_yt_dlp_config(self, user_agent):
        # YouTube handled by custom downloader.py
        # This config is for reference only
        return {
            "http_headers": {
                "User-Agent": user_agent,
            },
            "socket_timeout": 30,
            "retries": 8,
            "extractor_retries": 5,
            "format": "bestvideo+bestaudio/best",
        }
    
    def parse_error(self, error_msg):
        if "Video unavailable" in error_msg:
            return "YouTube video unavailable (removed, private, or region-locked)."
        elif "This video is private" in error_msg:
            return "This is a private YouTube video."
        elif "age" in error_msg.lower() and "restrict" in error_msg.lower():
            return "Age-restricted video. Add cookies from logged-in YouTube session."
        
        return super().parse_error(error_msg)
