"""Testes da interface em duas colunas e do quiz interativo."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from study_questions.config import ConfigError, Settings
from study_questions.models import Question, QuestionSet, QuestionType

APP_PATH = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def _app() -> AppTest:
    return AppTest.from_file(str(APP_PATH)).run()


def _fake_settings() -> Settings:
    return Settings(gemini_api_key="fake-test-key")


def _fake_open_question_set() -> QuestionSet:
    return QuestionSet(
        questions=[
            Question(
                type=QuestionType.OPEN,
                statement="O que é Python?",
                answer="Uma linguagem de programação.",
                explanation="O texto apresenta a definição.",
                source_excerpt="Python é uma linguagem de programação.",
            )
        ]
    )


def _fake_multiple_choice_set() -> QuestionSet:
    return QuestionSet(
        questions=[
            Question(
                type=QuestionType.MULTIPLE_CHOICE,
                statement="Qual linguagem é citada no documento?",
                answer="Python",
                explanation="Python é mencionada no texto.",
                source_excerpt="Python é uma linguagem de programação.",
                options=["Java", "Python", "Ruby"],
            )
        ]
    )


def _mock_generation(monkeypatch: pytest.MonkeyPatch, result: QuestionSet) -> None:
    def fake_generate(*args: object, **kwargs: object) -> QuestionSet:
        return result

    monkeypatch.setattr("study_questions.config.load_settings", _fake_settings)
    monkeypatch.setattr("study_questions.pipeline.generate_from_text", fake_generate)


def _upload_text(at: AppTest) -> AppTest:
    return (
        at.file_uploader[0]
        .upload(
            "aula.txt",
            "Python é uma linguagem de programação.".encode(),
            "text/plain",
        )
        .run()
    )


def _click_button(at: AppTest, label: str) -> AppTest:
    button = next(button for button in at.button if button.label == label)
    return button.click().run()


def test_interface_loads_without_api_key() -> None:
    at = _app()

    assert not at.exception
    assert at.title[0].value == "Perguntas de estudo"
    assert len(at.file_uploader) == 1
    assert len(at.download_button) == 0


def test_requires_document_before_generation() -> None:
    at = _app()
    at = _click_button(at, "Gerar perguntas")

    assert not at.exception
    assert any("Envie um documento" in item.value for item in at.warning)


def test_requires_question_type() -> None:
    at = _upload_text(_app())
    at.multiselect[0].set_value([]).run()
    at = _click_button(at, "Gerar perguntas")

    assert not at.exception
    assert any("pelo menos um tipo" in item.value for item in at.warning)


def test_generates_questions_without_real_api(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_generation(monkeypatch, _fake_open_question_set())
    at = _upload_text(_app())
    at = _click_button(at, "Gerar perguntas")

    assert not at.exception
    assert len(at.success) == 1
    assert len(at.download_button) == 2
    assert any(button.label == "Revelar resposta" for button in at.button)

    at.number_input[0].set_value(6).run()
    assert not at.exception
    assert len(at.download_button) == 0


def test_rejects_invalid_pdf() -> None:
    at = _app()
    at.file_uploader[0].upload(
        "aula.pdf",
        b"not a valid pdf",
        "application/pdf",
    ).run()
    at = _click_button(at, "Gerar perguntas")

    assert not at.exception
    assert any("Não foi possível gerar" in item.value for item in at.error)
    assert len(at.download_button) == 0


def test_displays_configuration_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def invalid_settings() -> Settings:
        raise ConfigError("Chave de API não configurada.")

    monkeypatch.setattr("study_questions.config.load_settings", invalid_settings)
    at = _upload_text(_app())
    at = _click_button(at, "Gerar perguntas")

    assert not at.exception
    assert any("Chave de API não configurada" in item.value for item in at.error)


def test_correct_choice_updates_score(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_generation(monkeypatch, _fake_multiple_choice_set())
    at = _upload_text(_app())
    at = _click_button(at, "Gerar perguntas")
    at = _click_button(at, "Python")

    assert not at.exception
    assert any("1 acerto(s)" in item.value for item in at.markdown)
    assert any("Correta" in item.value for item in at.markdown)
    assert len(at.download_button) == 2


def test_wrong_choice_updates_score(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_generation(monkeypatch, _fake_multiple_choice_set())
    at = _upload_text(_app())
    at = _click_button(at, "Gerar perguntas")
    at = _click_button(at, "Java")

    assert not at.exception
    assert any("1 erro(s)" in item.value for item in at.markdown)
    assert any("Incorreta" in item.value for item in at.markdown)


def test_open_question_self_assessment(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_generation(monkeypatch, _fake_open_question_set())
    at = _upload_text(_app())
    at = _click_button(at, "Gerar perguntas")
    at = _click_button(at, "Revelar resposta")
    at = _click_button(at, "Acertei")

    assert not at.exception
    assert any("1 acerto(s)" in item.value for item in at.markdown)
