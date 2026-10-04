import pytest
from pydantic import SecretStr, ValidationError

from template_fastapi_mcp.config import Settings


def _settings_data(**overrides):
    data = {
        "postgres_host": "postgres",
        "postgres_port": 5432,
        "postgres_user": "test_app",
        "postgres_password": "test-password",
        "dev_db_name": "template_fastapi_mcp",
        "test_db_name": "template_fastapi_mcp_test",
        "app_db_name": "template_fastapi_mcp_test",
        "app_port": 8000,
        "uvicorn_port": 8000,
        "test_http_port": 18000,
        "client_port": 6274,
    }
    data.update(overrides)
    return data


def test_database_url_escapes_reserved_password_characters():
    settings = Settings.model_validate(
        _settings_data(postgres_password="p@ss:w%rd")
    )
    rendered = settings.database_url.render_as_string(hide_password=False)
    assert "p%40ss%3Aw%25rd" in rendered
    assert "p@ss:w%rd" not in rendered


def test_settings_require_both_credentials(monkeypatch):
    monkeypatch.delenv("POSTGRES_USER", raising=False)
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    data = _settings_data()
    del data["postgres_user"]
    with pytest.raises(ValidationError):
        Settings.model_validate(data)
    data = _settings_data()
    del data["postgres_password"]
    with pytest.raises(ValidationError):
        Settings.model_validate(data)


def test_test_target_rejects_equal_database_names():
    settings = Settings.model_validate(
        _settings_data(
            dev_db_name="same_db",
            test_db_name="same_db",
            app_db_name="template_fastapi_mcp_test",
        )
    )
    with pytest.raises(ValueError, match="outside the test database"):
        settings.assert_test_target()


def test_test_target_rejects_development_database():
    settings = Settings.model_validate(
        _settings_data(app_db_name="template_fastapi_mcp")
    )
    with pytest.raises(ValueError, match="outside the test database"):
        settings.assert_test_target()


def test_settings_repr_and_url_mask_password():
    settings = Settings.model_validate(
        _settings_data(postgres_password="super-secret-value")
    )
    assert "super-secret-value" not in repr(settings)
    assert "super-secret-value" not in str(settings.database_url)
    assert "super-secret-value" not in settings.database_url.render_as_string()
