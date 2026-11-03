import pytest
from cryptography.fernet import Fernet

from app.config import Config, ConfigError

GOOD = {
    "DATABASE_URL": "postgresql+psycopg://u:p@localhost/db",
    "JWT_SECRET": "x" * 32,
    "GATEWAY_WEBHOOK_SECRET": "g" * 32,
    "PAN_ENCRYPTION_KEY": Fernet.generate_key().decode(),
}


def test_valid_config_loads_with_dev_defaults() -> None:
    cfg = Config.from_env(GOOD)
    assert cfg.app_env == "dev"
    assert cfg.cookie_secure is False


@pytest.mark.parametrize(
    "missing", ["DATABASE_URL", "JWT_SECRET", "PAN_ENCRYPTION_KEY", "GATEWAY_WEBHOOK_SECRET"]
)
def test_missing_required_value_refuses_to_boot(missing: str) -> None:
    env = {k: v for k, v in GOOD.items() if k != missing}
    with pytest.raises(ConfigError, match=missing):
        Config.from_env(env)


def test_short_jwt_secret_is_rejected() -> None:
    with pytest.raises(ConfigError, match="JWT_SECRET"):
        Config.from_env({**GOOD, "JWT_SECRET": "short"})


def test_invalid_fernet_key_is_rejected() -> None:
    with pytest.raises(ConfigError, match="PAN_ENCRYPTION_KEY"):
        Config.from_env({**GOOD, "PAN_ENCRYPTION_KEY": "not-a-key"})


def test_wildcard_cors_is_rejected() -> None:
    with pytest.raises(ConfigError, match="CORS_ORIGINS"):
        Config.from_env({**GOOD, "CORS_ORIGINS": "*"})


def test_prod_requires_origins_and_secure_cookies() -> None:
    with pytest.raises(ConfigError, match="CORS_ORIGINS"):
        Config.from_env({**GOOD, "APP_ENV": "prod"})
    cfg = Config.from_env({**GOOD, "APP_ENV": "prod", "CORS_ORIGINS": "https://example.org"})
    assert cfg.cookie_secure is True


def test_wrong_database_driver_is_rejected() -> None:
    with pytest.raises(ConfigError, match="DATABASE_URL"):
        Config.from_env({**GOOD, "DATABASE_URL": "sqlite:///x.db"})
