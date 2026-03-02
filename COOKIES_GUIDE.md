# Cookie Setup Guide for Instagram, Facebook, and Other Platforms

## Why Do You Need Cookies?

Some platforms like Instagram, Facebook, and Twitter/X may block or rate-limit requests without proper authentication. By providing browser cookies, the app can download videos as if you're logged in.

## How to Get Cookies

### Method 1: Browser Extension (Recommended)

1. **Install a Cookie Exporter Extension:**
   - Chrome/Edge: "Get cookies.txt LOCALLY" or "EditThisCookie"
   - Firefox: "cookies.txt" extension

2. **Export Cookies:**
   - Visit the website (e.g., instagram.com)
   - Make sure you're logged in
   - Click the extension icon
   - Export cookies as `cookies.txt` (Netscape format)

3. **Save the File:**
   - Save the file to your device's Downloads folder:
     - Android: `/storage/emulated/0/Download/videodownloader/cookies.txt`
     - PC: `~/Downloads/videodownloader/cookies.txt`

### Method 2: Platform-Specific Cookies

You can create separate cookie files for each platform:
- `instagram_cookies.txt` - For Instagram
- `facebook_cookies.txt` - For Facebook  
- `x_cookies.txt` - For Twitter/X

This allows different accounts for different platforms.

## Cookie File Location

The app looks for cookies in:
```
Android: /storage/emulated/0/Download/videodownloader/
Windows: C:\Users\YourName\Downloads\videodownloader\
Linux/Mac: ~/Downloads/videodownloader/
```

## Cookie File Format (Netscape)

The file should look like this:
```
# Netscape HTTP Cookie File
.instagram.com	TRUE	/	TRUE	1234567890	csrftoken	ABC123...
.instagram.com	TRUE	/	FALSE	1234567890	sessionid	XYZ789...
```

## Troubleshooting

### Still Getting Blocked?
1. Make sure cookies are fresh (exported recently)
2. Try logging out and back in on the website, then re-export
3. Check file permissions (must be readable by the app)
4. Some platforms require phone verification - complete that first

### Rate Limiting?
- Instagram: Wait 5-15 minutes between requests
- Facebook: Stricter rate limits, wait longer
- Use cookies to improve reliability

### Privacy Note
- Cookies contain your login session
- Keep them secure, don't share
- Regenerate cookies if you suspect they're compromised
- The app only uses cookies to download videos, nothing else

## Supported Platforms

✅ **Well Supported (with cookies):**
- Instagram
- Facebook
- Twitter/X
- TikTok
- Reddit
- Vimeo
- Dailymotion

⚠️ **May Require Cookies:**
- Instagram (stories, private accounts)
- Facebook (most videos)
- Twitter/X (some videos)

✅ **No Cookies Needed:**
- YouTube (always works)
- Most public video sites
