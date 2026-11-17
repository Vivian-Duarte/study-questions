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


def _fake_many_questions(count: int = 7) -> QuestionSet:
    """Cria questões independentes para testar a paginação e a pontuação."""
    return QuestionSet(
        questions=[
            Question(
                type=QuestionType.MULTIPLE_CHOICE,
                statement=f"Qual linguagem aparece na questão número {index + 1}?",
                answer="Python",
                explanation="A fonte menciona Python.",
                source_excerpt="Python é uma linguagem de programação.",
                options=["Java", "Python", "Ruby"],
            )
            for index in range(count)
        ]
    )


def test_page_bounds_never_exceed_available_questions() -> None:
    """Não permite páginas negativas nem índices maiores que o total."""
    from streamlit_app import _page_bounds

    assert _page_bounds(0, 3) == (0, 0, 0, 1)
    assert _page_bounds(5, 0) == (0, 5, 0, 1)
    assert _page_bounds(7, 0) == (0, 5, 0, 2)
    assert _page_bounds(7, 1) == (5, 7, 1, 2)
    assert _page_bounds(7, 50) == (5, 7, 1, 2)
    assert _page_bounds(7, -2) == (0, 5, 0, 2)


def test_paginates_questions_in_groups_of_five(monkeypatch: pytest.MonkeyPatch) -> None:
    """Renderiza apenas cinco cartões por página, usando índices estáveis."""
    _mock_generation(monkeypatch, _fake_many_questions())
    at = _click_button(_upload_text(_app()), "Gerar perguntas")

    assert not at.exception
    assert sum("PERGUNTA " in item.value for item in at.markdown) == 5
    assert any("PERGUNTA 1 DE 7" in item.value for item in at.markdown)
    assert any("Página 1 de 2" in item.value for item in at.markdown)

    at = _click_button(at, "Próxima")

    assert not at.exception
    assert sum("PERGUNTA " in item.value for item in at.markdown) == 2
    assert any("PERGUNTA 6 DE 7" in item.value for item in at.markdown)
    assert any("Página 2 de 2" in item.value for item in at.markdown)
    assert len(at.download_button) == 2


def test_quiz_score_persists_between_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mantém os acertos mesmo quando a pergunta não está mais na tela."""
    _mock_generation(monkeypatch, _fake_many_questions())
    at = _click_button(_upload_text(_app()), "Gerar perguntas")
    at = _click_button(at, "Python")
    at = _click_button(at, "Próxima")
    at = _click_button(at, "Python")

    assert not at.exception
    assert any("2 acerto(s)" in item.value for item in at.markdown)
    assert len(at.download_button) == 2


def test_new_generation_resets_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    """Uma nova geração começa sempre na primeira página."""
    _mock_generation(monkeypatch, _fake_many_questions())
    at = _click_button(_upload_text(_app()), "Gerar perguntas")
    at = _click_button(at, "Próxima")
    assert any("Página 2 de 2" in item.value for item in at.markdown)

    at = _click_button(at, "Gerar perguntas")

    assert not at.exception
    assert any("Página 1 de 2" in item.value for item in at.markdown)
    assert any("PERGUNTA 1 DE 7" in item.value for item in at.markdown)


def test_exports_are_not_rebuilt_when_answering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gera JSON/Anki uma vez, mesmo após interações com o quiz."""
    counts = {"json": 0, "anki": 0}

    def fake_json(question_set: QuestionSet) -> str:
        counts["json"] += 1
        return question_set.model_dump_json()

    def fake_anki(question_set: QuestionSet) -> str:
        counts["anki"] += 1
        return "example-tsv"

    monkeypatch.setattr("study_questions.exporters.export_json", fake_json)
    monkeypatch.setattr("study_questions.exporters.export_anki_tsv", fake_anki)
    _mock_generation(monkeypatch, _fake_multiple_choice_set())

    at = _click_button(_upload_text(_app()), "Gerar perguntas")
    assert counts == {"json": 1, "anki": 1}

    at = _click_button(at, "Python")

    assert not at.exception
    assert counts == {"json": 1, "anki": 1}


def test_generation_keeps_diagnostics_in_session_without_extra_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Armazena somente contadores e mantém a interface sem dados técnicos."""
    from study_questions.metrics import GenerationMetrics

    calls = 0

    def fake_generate(*args: object, **kwargs: object) -> QuestionSet:
        nonlocal calls
        calls += 1
        metrics = kwargs["metrics"]
        assert isinstance(metrics, GenerationMetrics)
        metrics.questions_requested += 2
        metrics.questions_received += 1
        metrics.questions_missing_from_response += 1
        metrics.questions_validated += 1
        metrics.questions_unique += 1
        return _fake_open_question_set()

    monkeypatch.setattr("study_questions.config.load_settings", _fake_settings)
    monkeypatch.setattr("study_questions.pipeline.generate_from_text", fake_generate)

    at = _click_button(_upload_text(_app()), "Gerar perguntas")
    assert not at.exception
    assert calls == 1
    recorded = at.session_state["generation_metrics"]
    assert isinstance(recorded, GenerationMetrics)
    assert recorded.questions_received == 1
    assert recorded.questions_missing_from_response == 1

    at = _click_button(at, "Revelar resposta")
    assert not at.exception
    assert calls == 1
    assert at.session_state["generation_metrics"].questions_received == 1
    assert not any("questions_missing_from_response" in item.value for item in at.markdown)


def test_diagnostics_are_replaced_for_each_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Uma nova geração não mistura contadores de execuções anteriores."""
    from study_questions.metrics import GenerationMetrics

    calls = 0

    def fake_generate(*args: object, **kwargs: object) -> QuestionSet:
        nonlocal calls
        calls += 1
        metrics = kwargs["metrics"]
        assert isinstance(metrics, GenerationMetrics)
        metrics.questions_received += calls
        return _fake_open_question_set()

    monkeypatch.setattr("study_questions.config.load_settings", _fake_settings)
    monkeypatch.setattr("study_questions.pipeline.generate_from_text", fake_generate)

    at = _click_button(_upload_text(_app()), "Gerar perguntas")
    first = at.session_state["generation_metrics"]
    assert first.questions_received == 1

    at = _click_button(at, "Gerar perguntas")
    second = at.session_state["generation_metrics"]
    assert not at.exception
    assert calls == 2
    assert second is not first
    assert second.questions_received == 2
