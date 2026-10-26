import pytest

from python_template.settings import Settings, load_settings


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("ENVIRONMENT", "PORT", "LOG_LEVEL", "SHUTDOWN_DRAIN_MS"):
        monkeypatch.delenv(name, raising=False)
    # Keep a developer's local .env out of the tests.
    monkeypatch.setitem(Settings.model_config, "env_file", None)


def test_defaults() -> None:
    settings = load_settings()
    assert settings.model_dump() == {
        "environment": "development",
        "port": 8080,
        "log_level": "info",
        "shutdown_drain_ms": 0,
    }


def test_lists_every_problem_by_name_without_values(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PORT", "not-a-port")
    monkeypatch.setenv("LOG_LEVEL", "loud")
    with pytest.raises(SystemExit) as exit_info:
        load_settings()
    assert exit_info.value.code == 1
    err = capsys.readouterr().err
    assert err.startswith("Invalid configuration:\n")
    assert "  PORT: " in err
    assert "  LOG_LEVEL: " in err
    assert "not-a-port" not in err
    assert "loud" not in err
