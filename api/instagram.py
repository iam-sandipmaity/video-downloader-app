"""
Instagram platform configuration.
Instagram is very aggressive with rate limiting and blocking.
Cookies are highly recommended for reliable downloads.
"""

from .base import BasePlatformConfig


class InstagramConfig(BasePlatformConfig):
    platform_name = "instagram"
    display_name = "Instagram"
    requires_cookies = True  # Strongly recommended
    has_separate_streams = False  # Usually combined streams
    cookie_filename = "instagram_cookies.txt"
    
    def get_yt_dlp_config(self, user_agent):
        return {
            "http_headers": {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-us,en;q=0.5",
                "Sec-Fetch-Mode": "navigate",
            },
            "socket_timeout": 30,
            "retries": 10,
            "extractor_retries": 10,
            "fragment_retries": 10,
        }
    
    def get_download_config(self, user_agent):
        config = self.get_yt_dlp_config(user_agent)
        config.update({
            "retries": 15,
            "extractor_retries": 12,
            "fragment_retries": 15,
            "socket_timeout": 45,
        })
        return config
    
    def get_format_selector(self):
        # Instagram provides combined video+audio
        return "best"
    
    def parse_error(self, error_msg):
        if "login" in error_msg.lower() or "checkpoint" in error_msg.lower():
            return "Instagram requires login. Export cookies from logged-in browser session."
        elif "429" in error_msg or "rate" in error_msg.lower():
            return "Instagram rate limiting detected. Wait 15-30 minutes or add fresh cookies."
        elif "challenge" in error_msg.lower():
            return "Instagram security challenge. Log in to Instagram in browser and re-export cookies."
        
        return super().parse_error(error_msg)
