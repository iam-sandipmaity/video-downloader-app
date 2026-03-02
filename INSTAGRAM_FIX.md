# Instagram Download Quick Fix Guide

## Problem: "No Video+Audio Options" or "Instagram Blocking"

### Quick Solution (Recommended)

**Use cookies to authenticate:**

1. **Get Cookie Extension:**
   - Install "[Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)" for Chrome/Edge
   - Or "cookies.txt" extension for Firefox

2. **Export Instagram Cookies:**
   ```
   1. Go to instagram.com and log in
   2. Click the extension icon
   3. Click "Export" → Save as "instagram_cookies.txt"
   ```

3. **Copy to App Folder:**
   ```
   Android path: /storage/emulated/0/Download/videodownloader/instagram_cookies.txt
   PC path: ~/Downloads/videodownloader/instagram_cookies.txt
   ```

4. **Try Download Again:**
   - Paste Instagram URL
   - Should now show multiple video+audio formats
   - No more blocking!

### Alternative: Wait It Out

If you don't want to use cookies:
- Instagram rate limits usually reset after 15-30 minutes
- Try from different network (WiFi ↔ Mobile data)
- Use VPN to change IP address

## Why It Happens

Instagram treats automated requests (like this app) differently from logged-in browser requests. They:
- Rate limit aggressive
- Block after just a few requests
- Only provide limited formats without authentication

Cookies make the app appear as a logged-in browser session → no blocking!

## Cookie Security

**Q: Are cookies safe to use?**
A: Yes, when stored locally:
- ✅ File stays on your device only
- ✅ App only uses it to download videos
- ✅ Not shared with anyone
- ⚠️ Keep file private (contains your session)

**Q: Will my account get banned?**
A: Very unlikely:
- You're just downloading public videos
- Instagram sees it as normal browsing
- Same as using browser

**Q: How often to update cookies?**
A: 
- Instagram cookies last weeks/months
- Update if you see "Login required" error
- Update after changing Instagram password

## What Formats to Expect

### With Cookies (Authenticated):
```
✅ Best Quality (Video+Audio) - 1080p/720p/480p
✅ Video Only options
✅ Audio Only options
```

### Without Cookies (Limited):
```
⚠️ Best Quality (Video+Audio) - Generic fallback
⚠️ May only get 1-2 formats
⚠️ May get blocked after first try
```

## Still Having Issues?

1. **Check cookie file location:**
   ```bash
   # Android (via file manager)
   Internal Storage → Download → videodownloader → instagram_cookies.txt
   
   # PC
   Downloads → videodownloader → instagram_cookies.txt
   ```

2. **Check cookie file format:**
   - Should be plain text
   - First line: `# Netscape HTTP Cookie File`
   - Multiple lines starting with `.instagram.com`

3. **Re-export fresh cookies:**
   - Log out of Instagram
   - Log back in
   - Export cookies again
   - Replace old file

4. **Check app logs:**
   - Open Diagnostics in app
   - Look for "Using cookies" message
   - If missing, file wasn't found

## Error Messages Explained

| Error | Meaning | Fix |
|-------|---------|-----|
| "429 Too Many Requests" | Rate limited | Add cookies or wait 30 min |
| "403 Forbidden" | Blocked | Add cookies |
| "Login required" | Private video or expired cookies | Update cookies |
| "Video not found" | Bad URL or deleted video | Check URL |

## Pro Tips

- 📱 Export cookies from phone's Chrome if downloading on phone
- 💾 Keep a backup copy of cookies.txt
- 🔄 Update cookies every month for best results
- 🌐 Works for Instagram stories, reels, and posts
- 👥 Can download from private accounts you follow (with cookies)

---

**Still stuck?** Check the full [COOKIES_GUIDE.md](COOKIES_GUIDE.md) for detailed instructions with screenshots.
