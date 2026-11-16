"""Testes automatizados da interface Streamlit."""

from collections.abc import Sequence
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from study_questions.config import ConfigError, Settings
from study_questions.models import Question, QuestionSet, QuestionType

APP_PATH = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def _app() -> AppTest:
    """Inicializa a interface em ambiente de teste."""
    return AppTest.from_file(str(APP_PATH)).run()


def _fake_settings() -> Settings:
    """Cria configurações sem utilizar credenciais reais."""
    return Settings(gemini_api_key="fake-test-key")


def _fake_question_set() -> QuestionSet:
    """Cria uma pergunta válida para simular a geração."""
    return QuestionSet(
        questions=[
            Question(
                type=QuestionType.OPEN,
                statement="O que é Python?",
                answer="Uma linguagem de programação.",
                explanation="O texto apresenta a definição.",
                source_excerpt=("Python é uma linguagem de programação."),
            )
        ]
    )


def test_interface_loads_without_api_key() -> None:
    """Abre a página sem exigir credenciais imediatamente."""
    at = _app()

    assert not at.exception
    assert at.title[0].value == "Study Questions"
    assert len(at.file_uploader) == 1
    assert len(at.download_button) == 0


def test_requires_document_before_generation() -> None:
    """Impede a geração sem um arquivo enviado."""
    at = _app()

    at.button[0].click().run()

    assert not at.exception
    assert len(at.warning) == 1
    assert "Envie um documento" in at.warning[0].value


def test_requires_question_type() -> None:
    """Impede a geração quando nenhum tipo está selecionado."""
    at = _app()

    at.file_uploader[0].upload(
        "aula.txt",
        b"Python facilita o estudo de programacao.",
        "text/plain",
    ).run()

    at.multiselect[0].set_value([]).run()
    at.button[0].click().run()

    assert not at.exception
    assert len(at.warning) == 1
    assert "pelo menos um tipo" in at.warning[0].value


def test_generates_questions_without_real_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Simula a geração e verifica os botões de exportação."""
    calls: list[int] = []

    def fake_generate(
        text: str,
        settings: Settings,
        *,
        question_count: int,
        question_types: Sequence[QuestionType],
    ) -> QuestionSet:
        """Retorna perguntas fictícias sem acessar o Gemini."""
        assert "Python" in text
        assert settings.gemini_api_key == "fake-test-key"
        assert QuestionType.OPEN in question_types
        calls.append(question_count)
        return _fake_question_set()

    monkeypatch.setattr(
        "study_questions.config.load_settings",
        _fake_settings,
    )
    monkeypatch.setattr(
        "study_questions.pipeline.generate_from_text",
        fake_generate,
    )

    at = _app()
    at.file_uploader[0].upload(
        "aula.txt",
        "Python é uma linguagem de programação.".encode(),
        "text/plain",
    ).run()

    at.button[0].click().run()

    assert not at.exception
    assert calls == [5]
    assert len(at.success) == 1
    assert len(at.download_button) == 2

    at.number_input[0].set_value(6).run()

    assert not at.exception
    assert len(at.download_button) == 0


def test_rejects_invalid_pdf() -> None:
    """Apresenta um erro quando o PDF não pode ser lido."""
    at = _app()

    at.file_uploader[0].upload(
        "aula.pdf",
        b"not a valid pdf",
        "application/pdf",
    ).run()

    at.button[0].click().run()

    assert not at.exception
    assert len(at.error) == 1
    assert "Não foi possível gerar" in at.error[0].value
    assert len(at.download_button) == 0


def test_displays_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exibe erros de configuração sem chamar a API real."""

    def invalid_settings() -> Settings:
        """Simula uma configuração ausente."""
        raise ConfigError("Chave de API não configurada.")

    monkeypatch.setattr(
        "study_questions.config.load_settings",
        invalid_settings,
    )

    at = _app()

    at.file_uploader[0].upload(
        "aula.txt",
        b"Python is a programming language.",
        "text/plain",
    ).run()

    at.button[0].click().run()

    assert not at.exception
    assert len(at.error) == 1
    assert "Chave de API não configurada" in at.error[0].value
