# API Platform Configuration System

## 📁 Structure

```
api/
├── __init__.py           # Main loader, exports all functions
├── base.py               # BasePlatformConfig class (all platforms inherit)
├── youtube.py            # YouTube config
├── instagram.py          # Instagram config
├── facebook.py           # Facebook config
├── tiktok.py             # TikTok config
├── twitter.py            # Twitter/X config
├── reddit.py             # Reddit config
├── vimeo.py              # Vimeo config
├── dailymotion.py        # Dailymotion config
├── twitch.py             # Twitch config
├── streamable.py         # Streamable config
└── README.md             # This file
```

## ✨ Adding a New Platform

### 1. Create Platform File

Create `api/yourplatform.py`:

```python
"""
YourPlatform configuration.
Brief description of platform-specific requirements.
"""

from .base import BasePlatformConfig


class YourPlatformConfig(BasePlatformConfig):
    platform_name = "yourplatform"  # URL identifier
    display_name = "YourPlatform"   # Display to users
    requires_cookies = False         # True if needs authentication
    has_separate_streams = False     # True if like YouTube (separate video/audio)
    cookie_filename = "yourplatform_cookies.txt"
    
    def get_yt_dlp_config(self, user_agent):
        """Config for info extraction."""
        return {
            "http_headers": {
                "User-Agent": user_agent,
                # Add platform-specific headers
            },
            "socket_timeout": 30,
            "retries": 5,
            "extractor_retries": 5,
            "format": self.get_format_selector(),
        }
    
    def get_download_config(self, user_agent):
        """Config for actual download (can override extraction config)."""
        config = self.get_yt_dlp_config(user_agent)
        config.update({
            "retries": 10,  # More retries for downloads
            "socket_timeout": 45,
        })
        return config
    
    def get_format_selector(self):
        """yt-dlp format selector string."""
        return "best[vcodec][acodec]/best"
    
    def parse_error(self, error_msg):
        """Convert technical errors to user-friendly messages."""
        if "specific error" in error_msg.lower():
            return "User-friendly explanation of what went wrong."
        
        # Fall back to base class error parsing
        return super().parse_error(error_msg)
```

### 2. Register in `__init__.py`

Add to `api/__init__.py`:

```python
from .yourplatform import YourPlatformConfig

PLATFORM_CONFIGS = {
    # ... existing platforms ...
    "yourplatform": YourPlatformConfig(),
}
```

### 3. Update Platform Detection

Add to `downloader_platforms.py` `detect_platform()`:

```python
if "yourplatform.com" in host:
    return "yourplatform"
```

### 4. Test

```python
# Test URL detection
url = "https://yourplatform.com/video/123"
platform = detect_platform(url)  # Should return "yourplatform"

# Test config loading
config = api.get_platform_config(platform)
print(config.display_name)  # Should print "YourPlatform"
```

## 🎨 Configuration Options

### Basic Properties

```python
platform_name = "instagram"        # Lowercase identifier
display_name = "Instagram"         # User-facing name
requires_cookies = True            # Recommend cookies?
has_separate_streams = False       # Separate video/audio like YouTube?
cookie_filename = "platform_cookies.txt"
```

### HTTP Headers

```python
def get_yt_dlp_config(self, user_agent):
    return {
        "http_headers": {
            "User-Agent": user_agent,
            "Referer": "https://platform.com/",      # Some need this
            "Accept-Language": "en-US,en;q=0.9",     # Language preference
            "Origin": "https://platform.com",         # CORS
        },
        # ... other config ...
    }
```

### Retry Settings

```python
# Conservative (stable platforms)
"retries": 5,
"extractor_retries": 5,
"socket_timeout": 30,

# Aggressive (flaky platforms like Instagram)
"retries": 15,
"extractor_retries": 12,
"socket_timeout": 45,
```

### Format Selection

```python
# Combined video+audio (most platforms)
"format": "best[vcodec][acodec]/best"

# Prefer highest quality
"format": "bestvideo+bestaudio/best"

# Specific resolution
"format": "bestvideo[height<=1080]+bestaudio/best"

# No watermark (TikTok)
"format": "best[vcodec][acodec]/best"
```

### Error Handling

```python
def parse_error(self, error_msg):
    """Add platform-specific error hints."""
    
    # Rate limiting
    if "429" in error_msg:
        return f"{self.display_name} rate limited. Wait 30 min or add cookies."
    
    # Authentication needed
    if "login" in error_msg.lower():
        return f"Login required. Export cookies from logged-in browser."
    
    # Private content
    if "private" in error_msg.lower():
        return "Private video. Need cookies from account that has access."
    
    # Geo-restricted
    if "geo" in error_msg.lower() or "region" in error_msg.lower():
        return "Video blocked in your region. Try VPN."
    
    # Fall back to base class
    return super().parse_error(error_msg)
```

## 📦 Using Platform Configs

### In Your Code

```python
import api

# Get config for platform
config = api.get_platform_config("instagram")

# Get yt-dlp options
ydl_opts = config.get_yt_dlp_config(user_agent="MyApp/1.0")

# Check if cookies needed
if config.requires_cookies:
    print(f"{config.display_name} works better with cookies!")

# Get cookie file path
cookie_path = api.get_cookie_file_path("instagram")
if cookie_path:
    ydl_opts["cookiefile"] = cookie_path

# Parse errors
try:
    # ... download ...
except Exception as e:
    friendly_msg = config.parse_error(str(e))
    print(friendly_msg)
```

### Helper Functions

```python
# Get all optimized platforms
platforms = api.get_all_platforms()
# ['dailymotion', 'facebook', 'instagram', 'reddit', ...]

# Get platforms needing cookies
cookie_platforms = api.get_platforms_requiring_cookies()
# ['instagram', 'facebook']

# Get cookie file location
cookie_file = api.get_cookie_file_path("instagram")
# /path/to/videodownloader/instagram_cookies.txt or None
```

## 🌟 Platform-Specific Tips

### Instagram
- **Requires cookies** for reliable access
- Rate limits aggressively (~5-10 requests before blocking)
- Use 15+ retries
- Fresh cookies (< 1 week old) work best

### Facebook
- **Requires cookies** for most videos
- Moderate rate limiting
- Works better with cookies from same region as video

### TikTok
- Usually works **without cookies**
- Can download without watermark
- Relatively stable API

### Twitter/X
- Public videos work **without cookies**
- Private accounts need cookies
- Rate limiting is moderate

### YouTube
- Handled by custom `downloader.py` (not this API system)
- Separate video/audio streams
- No cookies needed (except age-restricted)

## 🔧 Advanced Customization

### Platform-Specific Download Logic

```python
class ComplexPlatformConfig(BasePlatformConfig):
    def download(self, url, options):
        """Override entire download logic if needed."""
        # Custom download implementation
        pass
    
    def extract_formats(self, raw_formats):
        """Custom format parsing."""
        # Transform formats before showing to user
        pass
```

### Cookie Management

```python
def get_cookie_filename(self):
    """Custom cookie filename logic."""
    if self.platform_name == "instagram":
        # Try multiple locations
        return ["instagram_cookies.txt", "ig_cookies.txt"]
    return f"{self.platform_name}_cookies.txt"
```

## 📊 Testing Your Platform

```bash
# Test extraction
python -c "
import api
config = api.get_platform_config('yourplatform')
print(f'Platform: {config.display_name}')
print(f'Needs cookies: {config.requires_cookies}')
print(f'Cookie file: {config.get_cookie_filename()}')
"

# Test with real URL
python main.py
# Paste platform URL and check logs
```

## 🤝 Contributing New Platforms

1. Create platform file in `api/`
2. Register in `api/__init__.py`
3. Add URL detection in `downloader_platforms.py`
4. Test with real URLs
5. Document any cookie requirements
6. Submit PR with example URLs in commit message

## 🎯 Priority Platforms to Add

Based on popularity, consider adding:
- SoundCloud (music platform)
- Bandcamp (indie music)
- Spotify (podcasts)
- Bilibili (China)
- Niconico (Japan)
- BBC iPlayer (UK)
- Coursera (education)

Each addition is just one small file! 🚀
