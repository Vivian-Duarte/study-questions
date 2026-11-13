"""Testes iniciais dos modelos de domínio."""

import pytest
from pydantic import ValidationError

from study_questions.models import Question, QuestionSet, QuestionType


def make_multiple_choice(**overrides: object) -> dict[str, object]:
    """Monta dados de uma pergunta válida de múltipla escolha.

    Args:
        **overrides: Campos que substituem valores padrão.

    Returns:
        Dicionário de dados para validação.
    """
    data: dict[str, object] = {
        "type": QuestionType.MULTIPLE_CHOICE,
        "statement": "Qual é a capital da França?",
        "answer": "Paris",
        "explanation": "Paris é a capital da França.",
        "source_excerpt": "Paris é a capital da França.",
        "options": ["Paris", "Roma", "Madri"],
    }
    return data | overrides


def test_valid_multiple_choice() -> None:
    """Aceita uma pergunta de múltipla escolha válida."""
    question = Question.model_validate(make_multiple_choice())
    assert question.answer == "Paris"
    assert len(question.options) == 3


def test_valid_open_question() -> None:
    """Aceita pergunta aberta sem alternativas."""
    question = Question(
        type=QuestionType.OPEN,
        statement="O que é Python?",
        answer="Uma linguagem de programação.",
        source_excerpt="Python é uma linguagem de programação.",
    )
    assert question.options == []


@pytest.mark.parametrize(
    "options",
    [["Paris", "Roma"], ["Paris"] * 6],
)
def test_rejects_invalid_option_count(options: list[str]) -> None:
    """Rejeita quantidade de alternativas fora do intervalo permitido."""
    with pytest.raises(ValidationError, match="3 a 5"):
        Question.model_validate(make_multiple_choice(options=options))


def test_rejects_blank_option() -> None:
    """Rejeita alternativas vazias após normalização."""
    with pytest.raises(ValidationError, match="vazias"):
        Question.model_validate(make_multiple_choice(options=["Paris", "Roma", "   "]))


def test_rejects_duplicate_options() -> None:
    """Rejeita alternativas repetidas mesmo com letras diferentes."""
    with pytest.raises(ValidationError, match="duplicadas"):
        Question.model_validate(make_multiple_choice(options=["Paris", "PARIS", "Roma"]))


def test_rejects_incorrect_answer() -> None:
    """Exige que a resposta seja uma das alternativas."""
    with pytest.raises(ValidationError, match="corresponder exatamente"):
        Question.model_validate(make_multiple_choice(answer="Londres"))


def test_rejects_options_in_open_question() -> None:
    """Impede alternativas em perguntas abertas."""
    with pytest.raises(ValidationError, match="abertas"):
        Question.model_validate(make_multiple_choice(type=QuestionType.OPEN))


def test_strips_whitespace() -> None:
    """Remove espaços excedentes nos campos de texto."""
    question = Question.model_validate(
        make_multiple_choice(
            statement="  Capital da França?  ",
            options=["  Paris  ", "Roma", "Madri"],
        )
    )
    assert question.statement == "Capital da França?"
    assert question.options[0] == "Paris"


@pytest.mark.parametrize(
    "field",
    ["statement", "answer", "source_excerpt"],
)
def test_rejects_blank_required_field(field: str) -> None:
    """Rejeita campos obrigatórios compostos apenas por espaços."""
    with pytest.raises(ValidationError):
        Question.model_validate(make_multiple_choice(**{field: "   "}))


def test_rejects_extra_fields() -> None:
    """Rejeita campos inesperados enviados pelo modelo de linguagem."""
    with pytest.raises(ValidationError):
        Question.model_validate(make_multiple_choice(unexpected=True))


def test_rejects_empty_question_set() -> None:
    """Impede conjuntos sem perguntas."""
    with pytest.raises(ValidationError):
        QuestionSet(questions=[])


def test_question_set_from_json() -> None:
    """Valida JSON com perguntas aninhadas."""
    question = Question.model_validate(make_multiple_choice())
    original = QuestionSet(questions=[question])

    parsed = QuestionSet.model_validate_json(original.model_dump_json())

    assert parsed == original
