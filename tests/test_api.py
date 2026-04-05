"""Tests for the api/ platform configuration system."""

import pytest


class TestRegistry:
    def test_get_all_platforms_is_nonempty(self):
        import api
        platforms = api.get_all_platforms()
        assert len(platforms) >= 10

    def test_registered_platforms_have_reasonable_names(self):
        import api
        for name in api.get_all_platforms():
            assert name.islower()
            assert " " not in name


class TestPlatformConfigs:
    def test_instagram_requires_cookies(self):
        import api
        config = api.get_platform_config("instagram")
        assert config.requires_cookies is True

    def test_facebook_requires_cookies(self):
        import api
        config = api.get_platform_config("facebook")
        assert config.requires_cookies is True

    def test_youtube_no_cookies_required(self):
        import api
        config = api.get_platform_config("youtube")
        assert config.requires_cookies is False

    def test_unknown_platform_returns_fallback(self):
        import api
        config = api.get_platform_config("nonexistent_platform_xyz")
        from api import BasePlatformConfig
        assert isinstance(config, BasePlatformConfig)


class TestErrorParsing:
    def test_instagram_rate_limit(self):
        import api
        config = api.get_platform_config("instagram")
        msg = config.parse_error("HTTP Error 429: Too Many Requests")
        assert "rate" in msg.lower() or "cookie" in msg.lower()

    def test_generic_404(self):
        import api
        config = api.get_platform_config("youtube")
        msg = config.parse_error("Video not found")
        assert "not found" in msg.lower() or "unavailable" in msg.lower()

    def test_generic_403_suggests_cookies(self):
        import api
        config = api.get_platform_config("facebook")
        msg = config.parse_error("HTTP Error 403: Forbidden")
        assert "cookie" in msg.lower()

    def test_unknown_error_passthrough(self):
        import api
        config = api.get_platform_config("tiktok")
        msg = config.parse_error("Some weird error nobody has seen")
        assert "Some weird error nobody has seen" == msg


class TestCookieFile:
    def test_get_cookie_file_platform_specific(self, tmp_path, monkeypatch):
        import api
        import app_settings
        monkeypatch.setattr(app_settings, "get_data_dir", lambda: str(tmp_path))
        (tmp_path / "instagram_cookies.txt").write_text("test", encoding="utf-8")
        p = api.get_cookie_file_path("instagram")
        assert p is not None
        assert "instagram" in p.lower()

    def test_get_cookie_file_generic_fallback(self, tmp_path, monkeypatch):
        import api
        import app_settings
        monkeypatch.setattr(app_settings, "get_data_dir", lambda: str(tmp_path))
        (tmp_path / "cookies.txt").write_text("test", encoding="utf-8")
        p = api.get_cookie_file_path("unknown_xyz")
        assert p is not None
        assert "cookies.txt" in p

    def test_get_cookie_file_none_when_missing(self, tmp_path, monkeypatch):
        import api
        import app_settings
        monkeypatch.setattr(app_settings, "get_data_dir", lambda: str(tmp_path))
        p = api.get_cookie_file_path("nonexistent")
        assert p is None


class TestGetYtDlpConfig:
    def test_returns_dict_with_headers(self):
        import api
        config = api.get_platform_config("instagram")
        d = config.get_yt_dlp_config("test-ua")
        assert isinstance(d, dict)
        assert "http_headers" in d
        assert d["http_headers"]["User-Agent"] == "test-ua"

    def test_has_retries(self):
        import api
        config = api.get_platform_config("instagram")
        d = config.get_yt_dlp_config("test-ua")
        assert "retries" in d
        assert d["retries"] >= 5
