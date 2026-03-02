"""
Facebook platform configuration.
Facebook has strict rate limiting and often requires authentication.
"""

from .base import BasePlatformConfig


class FacebookConfig(BasePlatformConfig):
    platform_name = "facebook"
    display_name = "Facebook"
    requires_cookies = True
    has_separate_streams = False
    cookie_filename = "facebook_cookies.txt"
    
    def get_yt_dlp_config(self, user_agent):
        return {
            "http_headers": {
                "User-Agent": user_agent,
            },
            "socket_timeout": 30,
            "retries": 8,
            "extractor_retries": 8,
            "fragment_retries": 8,
        }
    
    def get_download_config(self, user_agent):
        config = self.get_yt_dlp_config(user_agent)
        config.update({
            "retries": 12,
            "socket_timeout": 45,
        })
        return config
    
    def get_format_selector(self):
        return "best"
    
    def parse_error(self, error_msg):
        if "login" in error_msg.lower():
            return "Facebook requires login. Add cookies from logged-in session."
        
        return super().parse_error(error_msg)
