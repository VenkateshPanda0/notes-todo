import os
import sys

import pytest

from backend.app.db import session


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for var in ("TASKFLOW_DATA_DIR", "APPDATA", "XDG_DATA_HOME", "DATABASE_URL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def test_override_wins_and_is_created(monkeypatch, tmp_path):
    target = tmp_path / "custom" / "data"
    monkeypatch.setenv("TASKFLOW_DATA_DIR", str(target))

    assert session.app_data_dir() == str(target)
    assert target.is_dir()


def test_windows_keeps_the_original_appdata_taskflow_folder(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))

    assert session.app_data_dir() == os.path.join(str(tmp_path / "Roaming"), "TaskFlow")


def test_windows_without_appdata_falls_back_to_the_user_profile(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "win32")

    assert session.app_data_dir().endswith(os.path.join("AppData", "Roaming", "TaskFlow"))


def test_macos_uses_application_support(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "darwin")

    assert session.app_data_dir().endswith(os.path.join("Library", "Application Support", "TaskFlow"))


def test_linux_honours_xdg_data_home(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))

    assert session.app_data_dir() == os.path.join(str(tmp_path / "xdg"), "taskflow")


def test_linux_defaults_to_local_share(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")

    assert session.app_data_dir().endswith(os.path.join(".local", "share", "taskflow"))


def test_frozen_build_stores_the_database_in_the_data_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("TASKFLOW_DATA_DIR", str(tmp_path / "d"))

    assert session.default_database_url() == f"sqlite:///{tmp_path / 'd' / 'flow.db'}"


def test_database_url_env_still_overrides_everything(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///elsewhere.db")

    assert session.default_database_url() == "sqlite:///elsewhere.db"


def test_source_runs_use_a_local_file(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)

    assert session.default_database_url() == "sqlite:///./flow.db"
