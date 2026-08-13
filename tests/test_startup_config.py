"""Tests for the Startup Configuration Contract (W7-5 Etapa 1).

Mandated coverage (Founder Decision, W7-5 Technical Design Approval +
Implementation Authorization): dev permissive; staging valid; staging
invalid; production valid; production invalid; ENVIRONMENT absent;
ENVIRONMENT invalid; absence of each critical config individually.

W7-1 Staging Deployment Readiness (Founder Decision, D-179) added coverage:
DATABASE_URL resolving to the default dev-only Postgres credentials
(`aipmo:aipmo@`) is rejected outside dev, same as SQLite.
"""
import pytest

from src.api.startup_config import (
    StartupConfigError,
    collect_startup_config_problems,
    resolve_environment,
    validate_startup_config,
)


class TestResolveEnvironment:
    def test_defaults_to_dev_when_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        assert resolve_environment() == "dev"

    @pytest.mark.parametrize("value", ["dev", "staging", "production"])
    def test_accepts_valid_values(self, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
        monkeypatch.setenv("ENVIRONMENT", value)
        assert resolve_environment() == value

    def test_is_case_insensitive_and_trims_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENVIRONMENT", "  PRODUCTION  ")
        assert resolve_environment() == "production"

    def test_rejects_invalid_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENVIRONMENT", "test")
        with pytest.raises(StartupConfigError, match="is invalid"):
            resolve_environment()


class TestDevPermissive:
    def test_no_problems_regardless_of_missing_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("API_KEY", raising=False)
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)
        monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
        assert collect_startup_config_problems("dev") == []
        validate_startup_config("dev")  # must not raise


@pytest.mark.parametrize("environment", ["staging", "production"])
class TestStagingAndProductionValid:
    def _set_valid_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DATABASE_URL", "postgresql://stratech_staging:real-db-secret@database:5432/stratech")
        monkeypatch.setenv("API_KEY", "real-key")
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "real-anthropic-key")
        monkeypatch.setenv("EMBEDDING_PROVIDER", "voyage")
        monkeypatch.setenv("VOYAGE_API_KEY", "real-voyage-key")
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com")

    def test_no_problems(self, monkeypatch: pytest.MonkeyPatch, environment: str) -> None:
        self._set_valid_env(monkeypatch)
        assert collect_startup_config_problems(environment) == []
        validate_startup_config(environment)  # must not raise


@pytest.mark.parametrize("environment", ["staging", "production"])
class TestStagingAndProductionInvalid:
    def _set_valid_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DATABASE_URL", "postgresql://stratech_staging:real-db-secret@database:5432/stratech")
        monkeypatch.setenv("API_KEY", "real-key")
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "real-anthropic-key")
        monkeypatch.setenv("EMBEDDING_PROVIDER", "voyage")
        monkeypatch.setenv("VOYAGE_API_KEY", "real-voyage-key")
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com")

    def test_missing_database_url(self, monkeypatch: pytest.MonkeyPatch, environment: str) -> None:
        self._set_valid_env(monkeypatch)
        monkeypatch.delenv("DATABASE_URL", raising=False)
        problems = collect_startup_config_problems(environment)
        assert any("DATABASE_URL is not set" in p for p in problems)
        with pytest.raises(StartupConfigError):
            validate_startup_config(environment)

    def test_database_url_resolves_to_sqlite(self, monkeypatch: pytest.MonkeyPatch, environment: str) -> None:
        self._set_valid_env(monkeypatch)
        monkeypatch.setenv("DATABASE_URL", "sqlite:///./ai_pmo_copilot.db")
        problems = collect_startup_config_problems(environment)
        assert any("resolves to SQLite" in p for p in problems)

    def test_database_url_uses_default_dev_credentials(
        self, monkeypatch: pytest.MonkeyPatch, environment: str
    ) -> None:
        self._set_valid_env(monkeypatch)
        monkeypatch.setenv("DATABASE_URL", "postgresql://aipmo:aipmo@database:5432/aipmo")
        problems = collect_startup_config_problems(environment)
        assert any("default development database credentials" in p for p in problems)
        with pytest.raises(StartupConfigError):
            validate_startup_config(environment)

    def test_missing_api_key(self, monkeypatch: pytest.MonkeyPatch, environment: str) -> None:
        self._set_valid_env(monkeypatch)
        monkeypatch.delenv("API_KEY", raising=False)
        problems = collect_startup_config_problems(environment)
        assert any("API_KEY is not set" in p for p in problems)

    def test_llm_provider_mock(self, monkeypatch: pytest.MonkeyPatch, environment: str) -> None:
        self._set_valid_env(monkeypatch)
        monkeypatch.setenv("LLM_PROVIDER", "mock")
        problems = collect_startup_config_problems(environment)
        assert any("LLM_PROVIDER=mock is not permitted" in p for p in problems)

    def test_anthropic_without_api_key(self, monkeypatch: pytest.MonkeyPatch, environment: str) -> None:
        self._set_valid_env(monkeypatch)
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        problems = collect_startup_config_problems(environment)
        assert any("ANTHROPIC_API_KEY is not set" in p for p in problems)

    def test_embedding_provider_mock(self, monkeypatch: pytest.MonkeyPatch, environment: str) -> None:
        self._set_valid_env(monkeypatch)
        monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")
        problems = collect_startup_config_problems(environment)
        assert any("EMBEDDING_PROVIDER=mock is not permitted" in p for p in problems)

    def test_voyage_without_api_key(self, monkeypatch: pytest.MonkeyPatch, environment: str) -> None:
        self._set_valid_env(monkeypatch)
        monkeypatch.setenv("EMBEDDING_PROVIDER", "voyage")
        monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
        problems = collect_startup_config_problems(environment)
        assert any("VOYAGE_API_KEY is not set" in p for p in problems)

    def test_missing_cors_allowed_origins(self, monkeypatch: pytest.MonkeyPatch, environment: str) -> None:
        self._set_valid_env(monkeypatch)
        monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
        problems = collect_startup_config_problems(environment)
        assert any("CORS_ALLOWED_ORIGINS is not set" in p for p in problems)

    def test_multiple_problems_are_all_reported(self, monkeypatch: pytest.MonkeyPatch, environment: str) -> None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("API_KEY", raising=False)
        monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
        monkeypatch.setenv("LLM_PROVIDER", "mock")
        monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")
        problems = collect_startup_config_problems(environment)
        assert len(problems) == 5
        with pytest.raises(StartupConfigError, match="5 critical configuration problem"):
            validate_startup_config(environment)
