"""Tests for batch_download.py — URL extraction and classification."""

from batch_download import extract_urls, is_supported_platform, classify_urls


class TestExtractUrls:
    def test_empty_string(self):
        assert extract_urls("") == []

    def test_none(self):
        assert extract_urls(None) == []

    def test_single_url(self):
        urls = extract_urls("https://www.youtube.com/watch?v=abc123")
        assert len(urls) == 1
        assert "youtube.com" in urls[0]

    def test_multiple_urls(self):
        text = "Check https://youtu.be/x and https://instagram.com/reel/42"
        urls = extract_urls(text)
        assert len(urls) == 2

    def test_deduplication(self):
        text = "https://youtube.com/watch?v=abc https://youtube.com/watch?v=abc"
        urls = extract_urls(text)
        assert len(urls) == 1

    def test_strips_trailing_punctuation(self):
        text = "Look: https://youtube.com/watch?v=abc."
        urls = extract_urls(text)
        assert urls[0].endswith("abc")
        assert not urls[0].endswith(".")

    def test_non_url_text(self):
        assert extract_urls("just some text without urls") == []

    def test_unsupported_scheme(self):
        assert extract_urls("ftp://example.com/file") == []


class TestIsSupportedPlatform:
    def test_youtube(self):
        assert is_supported_platform("https://www.youtube.com/watch?v=x")

    def test_instagram(self):
        assert is_supported_platform("https://www.instagram.com/reel/abc")

    def test_x_twitter(self):
        assert is_supported_platform("https://x.com/user/status/123")

    def test_unknown(self):
        assert not is_supported_platform("https://randomsite.com/page")

    def test_empty_url(self):
        assert not is_supported_platform("")


class TestClassifyUrls:
    def test_mixed_urls(self):
        text = "https://youtube.com/watch?v=1 https://randomsite.com/page"
        result = classify_urls(text)
        assert len(result["urls"]) == 2
        assert result["supported"] == 1
        assert result["unknown"] == 1

    def test_all_supported(self):
        text = "https://youtu.be/a https://instagram.com/reel/b"
        result = classify_urls(text)
        assert result["supported"] == 2
        assert result["unknown"] == 0

    def test_no_urls(self):
        result = classify_urls("just text")
        assert result["urls"] == []
        assert result["supported"] == 0
        assert result["unknown"] == 0
