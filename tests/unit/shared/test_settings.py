from vault_shared.settings import Settings


def test_defaults_are_safe_for_local_development() -> None:
    settings = Settings(_env_file=None)

    assert settings.environment == "development"
    assert settings.database_url.startswith("postgresql")
    assert settings.redis_url.startswith("redis://")


def test_cors_origins_list_splits_and_strips_comma_separated_env_value() -> None:
    settings = Settings(_env_file=None, cors_allow_origins="http://a.test, http://b.test ,,")

    assert settings.cors_origins_list == ["http://a.test", "http://b.test"]


def test_reads_overrides_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "from-env")
    monkeypatch.setenv("SERVICE_NAME", "vault-backend-test")

    settings = Settings(_env_file=None)

    assert settings.jwt_secret == "from-env"
    assert settings.service_name == "vault-backend-test"
