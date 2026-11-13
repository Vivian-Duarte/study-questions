"""Carregamento e validação das configurações da aplicação."""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from dotenv import load_dotenv

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_CHUNK_WORDS = 1000


class ConfigError(RuntimeError):
    """Representa um erro de configuração da aplicação."""


@dataclass(frozen=True, slots=True)
class Settings:
    """Armazena as configurações validadas da aplicação.

    Attributes:
        gemini_api_key: Chave de acesso à API do Gemini.
        gemini_model: Modelo utilizado na geração de perguntas.
        max_chunk_words: Quantidade máxima de palavras por bloco.
    """

    gemini_api_key: str = field(repr=False)
    gemini_model: str = DEFAULT_GEMINI_MODEL
    max_chunk_words: int = DEFAULT_CHUNK_WORDS


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Carrega e valida as variáveis de ambiente.

    Args:
        env: Variáveis utilizadas na configuração. Quando None,
            carrega o arquivo .env e utiliza os.environ.

    Returns:
        Objeto imutável contendo as configurações validadas.

    Raises:
        ConfigError: Quando uma configuração obrigatória estiver
            ausente ou possuir um valor inválido.
    """
    if env is None:
        load_dotenv()
        env = os.environ

    api_key = env.get("GEMINI_API_KEY", "").strip()

    if not api_key:
        raise ConfigError("A variável GEMINI_API_KEY é obrigatória.")

    model = env.get(
        "GEMINI_MODEL",
        DEFAULT_GEMINI_MODEL,
    ).strip()

    if not model:
        raise ConfigError("GEMINI_MODEL não pode estar vazio.")

    raw_chunk_words = env.get(
        "MAX_CHUNK_WORDS",
        str(DEFAULT_CHUNK_WORDS),
    ).strip()

    try:
        max_chunk_words = int(raw_chunk_words)
    except ValueError as exc:
        raise ConfigError("MAX_CHUNK_WORDS deve ser um número inteiro.") from exc

    if max_chunk_words < 1:
        raise ConfigError("MAX_CHUNK_WORDS deve ser maior que zero.")

    return Settings(
        gemini_api_key=api_key,
        gemini_model=model,
        max_chunk_words=max_chunk_words,
    )
