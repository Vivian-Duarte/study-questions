"""Testes do carregamento das configurações."""

from unittest.mock import Mock

import pytest

from study_questions.config import (
    DEFAULT_CHUNK_WORDS,
    DEFAULT_GEMINI_MODEL,
    ConfigError,
    load_settings,
)


def test_loads_default_settings() -> None:
    """Carrega as configurações padrão com a chave obrigatória."""
    settings = load_settings({"GEMINI_API_KEY": "test-key"})

    assert settings.gemini_api_key == "test-key"
    assert settings.gemini_model == DEFAULT_GEMINI_MODEL
    assert settings.max_chunk_words == DEFAULT_CHUNK_WORDS


def test_loads_custom_settings() -> None:
    """Aceita configurações personalizadas válidas."""
    settings = load_settings(
        {
            "GEMINI_API_KEY": "custom-key",
            "GEMINI_MODEL": "custom-model",
            "MAX_CHUNK_WORDS": "500",
        }
    )

    assert settings.gemini_model == "custom-model"
    assert settings.max_chunk_words == 500


def test_rejects_missing_api_key() -> None:
    """Rejeita configurações sem a chave do Gemini."""
    with pytest.raises(ConfigError, match="GEMINI_API_KEY"):
        load_settings({})


def test_rejects_blank_api_key() -> None:
    """Rejeita chaves compostas apenas por espaços."""
    with pytest.raises(ConfigError, match="GEMINI_API_KEY"):
        load_settings({"GEMINI_API_KEY": "   "})


def test_rejects_blank_model() -> None:
    """Rejeita nomes de modelo vazios."""
    with pytest.raises(ConfigError, match="GEMINI_MODEL"):
        load_settings(
            {
                "GEMINI_API_KEY": "test-key",
                "GEMINI_MODEL": "   ",
            }
        )


@pytest.mark.parametrize(
    "value",
    ["abc", "0", "-3", ""],
)
def test_rejects_invalid_chunk_size(value: str) -> None:
    """Rejeita limites de palavras inválidos."""
    with pytest.raises(ConfigError, match="MAX_CHUNK_WORDS"):
        load_settings(
            {
                "GEMINI_API_KEY": "test-key",
                "MAX_CHUNK_WORDS": value,
            }
        )


def test_hides_api_key_in_repr() -> None:
    """Impede que a representação exponha a chave de API."""
    settings = load_settings({"GEMINI_API_KEY": "secret-test-key"})

    assert "secret-test-key" not in repr(settings)


def test_loads_settings_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Carrega configurações do ambiente sem acessar o arquivo real."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-test-key")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("MAX_CHUNK_WORDS", raising=False)

    fake_dotenv = Mock(return_value=False)

    monkeypatch.setattr(
        "study_questions.config.load_dotenv",
        fake_dotenv,
    )

    settings = load_settings()

    assert settings.gemini_api_key == "fake-test-key"
    assert settings.gemini_model == DEFAULT_GEMINI_MODEL
    assert settings.max_chunk_words == DEFAULT_CHUNK_WORDS

    fake_dotenv.assert_called_once_with()
