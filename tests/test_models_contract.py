"""Testes adicionais dos contratos de dados das perguntas de estudo."""

import pytest
from pydantic import ValidationError

from study_questions.models import Question, QuestionSet, QuestionType


def _valid_question_payload() -> dict[str, object]:
    """Cria dados válidos de múltipla escolha para os testes.

    Returns:
        Dicionário com os campos de uma pergunta válida.
    """
    return {
        "type": "multiple_choice",
        "statement": "Qual é a capital da França?",
        "answer": "Paris",
        "source_excerpt": "Paris é a capital da França.",
        "options": ["Paris", "Roma", "Madri"],
    }


@pytest.mark.parametrize("amount", [3, 4, 5])
def test_accepts_valid_option_boundaries(amount: int) -> None:
    """Aceita o limite mínimo, valores intermediários e o máximo."""
    options = ["Paris", "Roma", "Madri", "Berlim", "Lisboa"][:amount]

    question = Question.model_validate({**_valid_question_payload(), "options": options})

    assert len(question.options) == amount


@pytest.mark.parametrize("invalid_type", ["true_false", "", 42, None])
def test_rejects_unknown_question_types(invalid_type: object) -> None:
    """Rejeita tipos desconhecidos ou inválidos."""
    with pytest.raises(ValidationError):
        Question.model_validate({**_valid_question_payload(), "type": invalid_type})


@pytest.mark.parametrize(
    "field",
    ["type", "statement", "answer", "source_excerpt"],
)
def test_rejects_missing_required_fields(field: str) -> None:
    """Rejeita campos obrigatórios ausentes."""
    payload = _valid_question_payload()
    del payload[field]

    with pytest.raises(ValidationError):
        Question.model_validate(payload)


@pytest.mark.parametrize(
    "options",
    ["Paris, Roma, Madri", None, 123],
)
def test_rejects_options_that_are_not_lists(options: object) -> None:
    """Exige que as alternativas sejam fornecidas como lista."""
    with pytest.raises(ValidationError):
        Question.model_validate({**_valid_question_payload(), "options": options})


def test_rejects_statement_shorter_than_five_chars_after_trim() -> None:
    """Rejeita enunciado abaixo do mínimo após remover espaços."""
    with pytest.raises(ValidationError):
        Question.model_validate({**_valid_question_payload(), "statement": "  ABC  "})


@pytest.mark.parametrize(
    "raw",
    ['{"questions": [', '[{"questions": []}]'],
)
def test_rejects_malformed_or_wrong_root_json(raw: str) -> None:
    """Rejeita JSON malformado ou com estrutura incorreta."""
    with pytest.raises(ValidationError):
        QuestionSet.model_validate_json(raw)


def test_rejects_empty_question_set_from_json() -> None:
    """Rejeita conjuntos vazios recebidos em JSON."""
    with pytest.raises(ValidationError):
        QuestionSet.model_validate_json('{"questions": []}')


def test_rejects_extra_fields_in_question_set() -> None:
    """Rejeita campos desconhecidos dentro de QuestionSet."""
    with pytest.raises(ValidationError):
        QuestionSet.model_validate(
            {
                "questions": [_valid_question_payload()],
                "unexpected": "value",
            }
        )


def test_rejects_invalid_question_nested_in_set() -> None:
    """Rejeita o conjunto quando uma pergunta é inválida."""
    invalid = {
        **_valid_question_payload(),
        "answer": "Londres",
    }

    with pytest.raises(ValidationError):
        QuestionSet.model_validate(
            {
                "questions": [
                    _valid_question_payload(),
                    invalid,
                ]
            }
        )


def test_accepts_mixed_question_types_in_set() -> None:
    """Aceita perguntas abertas e de múltipla escolha juntas."""
    multiple_choice = Question.model_validate(_valid_question_payload())

    open_question = Question(
        type=QuestionType.OPEN,
        statement="Explique o que é Python.",
        answer="Uma linguagem de programação.",
        source_excerpt="Python é uma linguagem de programação.",
    )

    result = QuestionSet(questions=[multiple_choice, open_question])

    assert [question.type for question in result.questions] == [
        QuestionType.MULTIPLE_CHOICE,
        QuestionType.OPEN,
    ]


def test_preserves_unicode_during_json_roundtrip() -> None:
    """Preserva acentos e caracteres Unicode no JSON."""
    question = Question(
        type=QuestionType.OPEN,
        statement="O que é programação?",
        answer="Criação de instruções. 😊",
        source_excerpt="A programação permite construir soluções.",
    )

    original = QuestionSet(questions=[question])

    assert QuestionSet.model_validate_json(original.model_dump_json()) == original


def test_default_options_are_independent() -> None:
    """Garante listas de alternativas independentes entre perguntas."""
    data = {
        "type": "open",
        "statement": "O que é Python?",
        "answer": "Uma linguagem de programação.",
        "source_excerpt": "Python é uma linguagem de programação.",
    }

    first = Question.model_validate(data)
    second = Question.model_validate(data)

    assert first.options is not second.options


def test_rejects_duplicate_options_after_trim_and_casefold() -> None:
    """Detecta alternativas duplicadas com espaços e caixa diferente."""
    with pytest.raises(ValidationError, match="duplicadas"):
        Question.model_validate(
            {
                **_valid_question_payload(),
                "options": [" Paris ", "PARIS", "Roma"],
            }
        )


def test_answer_must_match_option_exactly() -> None:
    """Exige correspondência exata entre resposta e alternativa."""
    with pytest.raises(ValidationError, match="exatamente"):
        Question.model_validate({**_valid_question_payload(), "answer": "paris"})
