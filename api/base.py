"""
Base platform configuration class.
All platform-specific configs should inherit from this.
"""


class BasePlatformConfig:
    """Base class for platform-specific configurations."""
    
    # Platform identifier (e.g., "youtube", "instagram")
    platform_name = "generic"
    
    # Display name for logs/UI
    display_name = "Generic Platform"
    
    # Does this platform typically require cookies?
    requires_cookies = False
    
    # Does this platform provide separate video/audio streams?
    has_separate_streams = False
    
    # Cookie filename (e.g., "instagram_cookies.txt")
    cookie_filename = None
    
    def get_yt_dlp_config(self, user_agent):
        """
        Returns yt-dlp configuration dictionary for this platform.
        
        Args:
            user_agent: User agent string to use
            
        Returns:
            dict: Configuration options for yt-dlp
        """
        return {
            "http_headers": {
                "User-Agent": user_agent,
            },
            "socket_timeout": 30,
            "retries": 5,
            "extractor_retries": 5,
            "fragment_retries": 5,
        }
    
    def get_download_config(self, user_agent):
        """
        Returns download-specific configuration.
        Can override extraction config with download-specific settings.
        
        Args:
            user_agent: User agent string to use
            
        Returns:
            dict: Configuration options for downloading
        """
        config = self.get_yt_dlp_config(user_agent)
        # Download typically needs more retries
        config.update({
            "retries": 10,
            "fragment_retries": 10,
            "socket_timeout": 45,
        })
        return config
    
    def get_format_selector(self):
        """
        Returns the format selector string for yt-dlp.
        Override for platform-specific format preferences.
        
        Returns:
            str: Format selector (e.g., "best", "bestvideo+bestaudio")
        """
        return "best"
    
    def parse_error(self, error_msg):
        """
        Parse and enhance error messages for better user feedback.
        Override for platform-specific error handling.
        
        Args:
            error_msg: Raw error message from yt-dlp
            
        Returns:
            str: User-friendly error message
        """
        if "429" in error_msg or "Too Many Requests" in error_msg:
            return f"{self.display_name} is rate limiting. Wait a few minutes or add cookies."
        elif "403" in error_msg or "Forbidden" in error_msg:
            return f"{self.display_name} blocked the request. Try using cookies."
        elif "404" in error_msg or "not found" in error_msg.lower():
            return "Video not found or has been removed."
        elif "Login required" in error_msg or "Sign in" in error_msg:
            return f"{self.display_name} requires login. Add cookies file."
        elif "Private video" in error_msg or "private" in error_msg.lower():
            return "This video is private. You need to be logged in (cookies)."
        
        return error_msg
    
    def get_cookie_filename(self):
        """Returns the cookie filename for this platform."""
        return self.cookie_filename or f"{self.platform_name}_cookies.txt"
