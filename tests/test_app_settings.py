"""Tests for app_settings.py — pure Python, no Kivy required."""

import json
import os
import pathlib
import tempfile
import threading
import time

import pytest

# Patch the data dir before importing the module.
@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path, monkeypatch):
    """Redirect every settings / history / backup call to a fresh tmp dir."""
    monkeypatch.setenv("HOME", str(tmp_path))

    def fake_external():
        return str(tmp_path / "Download" / "videodownloader")

    # Patch at the module level
    import app_settings
    monkeypatch.setattr(app_settings, "get_data_dir", fake_external)
    monkeypatch.setattr(app_settings, "_external_base", fake_external)

    # Ensure the directory exists
    os.makedirs(str(tmp_path / "Download" / "videodownloader"), exist_ok=True)

    yield


class TestDefaults:
    def test_defaults_has_required_keys(self):
        from app_settings import _defaults
        d = _defaults()
        assert isinstance(d, dict)
        for key in ("download_dir", "theme", "theme_mode", "notifications"):
            assert key in d

    def test_default_theme_is_dark(self):
        from app_settings import DEFAULT_THEME, DEFAULT_THEME
        assert DEFAULT_THEME == "Neon Dusk"


class TestLoadSaveSettings:
    def test_save_and_reload(self):
        import app_settings
        app_settings.save_settings({"theme": "custom"})
        loaded = app_settings.load_settings()
        assert loaded["theme"] == "custom"

    def test_missing_keys_filled_by_defaults(self):
        import app_settings
        app_settings.save_settings({})
        loaded = app_settings.load_settings()
        assert "download_dir" in loaded
        assert "notifications" in loaded

    def test_corrupt_file_returns_defaults(self, monkeypatch):
        import app_settings
        p = pathlib.Path(app_settings.settings_path())
        p.write_text("{bad json", encoding="utf-8")
        d = app_settings.load_settings()
        assert isinstance(d, dict)
        assert d["theme"] == "Neon Dusk"


class TestHistory:
    def test_append_and_load(self):
        import app_settings
        app_settings.clear_history()
        app_settings.append_history({"name": "test", "path": "/dev/null"})
        items = app_settings.load_history()
        assert len(items) == 1
        assert items[0]["name"] == "test"

    def test_limit_truncates(self):
        import app_settings
        app_settings.clear_history()
        # Minimum enforced limit is 10 (see max(10, ...) in append_history)
        for i in range(15):
            app_settings.append_history({"name": f"v{i}", "path": ""}, limit=10)
        items = app_settings.load_history()
        assert len(items) <= 10
        assert items[-1]["name"] == "v14"

    def test_delete_item(self):
        import app_settings
        app_settings.clear_history()
        app_settings.append_history({"name": "keep"}, limit=10)
        app_settings.append_history({"name": "drop"}, limit=10)
        items = app_settings.load_history()
        drop_id = items[0]["id"]
        app_settings.delete_history_item(drop_id)
        assert not any(x["id"] == drop_id for x in app_settings.load_history())

    def test_clear_history(self):
        import app_settings
        app_settings.clear_history()
        app_settings.append_history({"name": "x"}, limit=10)
        app_settings.clear_history()
        assert app_settings.load_history() == []


class TestBackupRestore:
    def test_create_and_list(self):
        import app_settings
        app_settings.save_settings({"theme": "t1"})
        app_settings.create_backup()
        backups = app_settings.list_backups(limit=1)
        assert len(backups) >= 1
        assert "path" in backups[0]

    def test_round_trip(self):
        import app_settings
        app_settings.save_settings({"theme": "original"})
        app_settings.clear_history()
        app_settings.append_history({"name": "h1"}, limit=10)

        bp = app_settings.create_backup()
        app_settings.save_settings({"theme": "modified"})
        app_settings.clear_history()

        app_settings.restore_backup(bp)
        s = app_settings.load_settings()
        assert s["theme"] == "original"
        assert len(app_settings.load_history()) >= 1

    def test_restore_missing_file(self):
        import app_settings
        with pytest.raises(FileNotFoundError):
            app_settings.restore_backup("/nonexistent/backup.json")


class TestDownloadDir:
    def test_get_download_dir_returns_a_string(self):
        import app_settings
        d = app_settings.get_download_dir()
        assert isinstance(d, str)
        assert os.path.isdir(d)

    def test_set_download_dir(self, tmp_path):
        import app_settings
        new_dir = str(tmp_path / "custom_dl")
        result = app_settings.set_download_dir(new_dir)
        assert result == new_dir
        assert os.path.isdir(new_dir)
        assert app_settings.get_download_dir() == new_dir


class TestToggleSetters:
    def test_notifications_toggle(self):
        import app_settings
        app_settings.set_notifications(False)
        assert app_settings.load_settings()["notifications"] is False
        app_settings.set_notifications(True)
        assert app_settings.load_settings()["notifications"] is True

    def test_resume_downloads_toggle(self):
        import app_settings
        app_settings.set_resume_downloads(True)
        assert app_settings.load_settings()["resume_downloads"] is True

    def test_auto_cleanup_cache_toggle(self):
        import app_settings
        app_settings.set_auto_cleanup_cache(False)
        assert app_settings.load_settings()["auto_cleanup_cache"] is False

    def test_cache_max_age_hours(self):
        import app_settings
        app_settings.set_cache_max_age_hours(24)
        assert app_settings.load_settings()["cache_max_age_hours"] == 24

    def test_max_crash_log_mb(self):
        import app_settings
        app_settings.set_max_crash_log_mb(5)
        assert app_settings.max_crash_log_bytes() == 5 * 1024 * 1024

    def test_history_limit(self):
        import app_settings
        app_settings.set_history_limit(50)
        assert app_settings.load_settings()["history_limit"] == 50

    def test_diagnostics_live_toggle(self):
        import app_settings
        app_settings.set_diagnostics_live(False)
        assert app_settings.load_settings()["diagnostics_live"] is False

    def test_theme_mode_switch(self):
        import app_settings
        app_settings.set_theme_mode("light")
        assert app_settings.load_settings()["theme_mode"] == "light"
        app_settings.set_theme_mode("dark")
        assert app_settings.load_settings()["theme_mode"] == "dark"


class TestBatchUpdate:
    def test_update_settings_single_load(self):
        import app_settings
        result = app_settings.update_settings({"theme": "batch_t", "notifications": False})
        assert result["theme"] == "batch_t"
        assert result["notifications"] is False
        # Verify persisted
        reloaded = app_settings.load_settings()
        assert reloaded["theme"] == "batch_t"


class TestThreadSafety:
    def test_concurrent_saves_do_not_corrupt(self):
        import app_settings
        errors = []

        def worker(n):
            try:
                app_settings.save_settings({"worker": n, "theme": f"t{n}"})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent saves errored: {errors}"
        # Final state should be valid
        s = app_settings.load_settings()
        assert "worker" in s
