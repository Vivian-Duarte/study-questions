"""Testes do contrato JSON nativo usado na API Gemini."""

import pytest
from pydantic import ValidationError

from study_questions.models import Question, QuestionSet, QuestionType
from study_questions.output_schema import GeneratedQuestion, GeneratedQuestions


def _generated_question() -> dict[str, object]:
    return {
        "type": "multiple_choice",
        "statement": "Qual é a linguagem citada?",
        "answer": "Python",
        "explanation": "Python aparece no trecho.",
        "source_excerpt": "Python é uma linguagem.",
        "options": ["Python", "Ruby", "Java"],
    }


def test_schema_allows_empty_response_for_insufficient_material() -> None:
    """Não impõe minItems=1 como QuestionSet, que trata resultado final."""
    batch = GeneratedQuestions.model_validate({"questions": []})
    assert batch.questions == []
    with pytest.raises(ValidationError):
        QuestionSet.model_validate({"questions": []})


def test_schema_has_same_question_fields_as_domain() -> None:
    """Evita drift entre o contrato da API e o domínio da aplicação."""
    assert set(GeneratedQuestion.model_fields) == set(Question.model_fields)
    assert set(GeneratedQuestions.model_fields) == {"questions"}


def test_schema_supports_supported_question_types() -> None:
    """Gera um contrato Pydantic com o enum de tipos do domínio."""
    question = GeneratedQuestion.model_validate(_generated_question())
    assert question.type is QuestionType.MULTIPLE_CHOICE


def test_schema_leaves_cross_field_validation_to_domain() -> None:
    """Uma alternativa inválida não deve comprometer a leitura do lote."""
    invalid = _generated_question()
    invalid["answer"] = "Resposta não presente nas alternativas"
    batch = GeneratedQuestions.model_validate({"questions": [_generated_question(), invalid]})

    assert len(batch.questions) == 2
    with pytest.raises(ValidationError):
        Question.model_validate(invalid)


def test_schema_requires_question_fields() -> None:
    """Campos ausentes não correspondem ao contrato enviado ao Gemini."""
    with pytest.raises(ValidationError):
        GeneratedQuestions.model_validate({"questions": [{"type": "open"}]})


def test_schema_json_schema_is_object_with_questions_array() -> None:
    """Confirma a estrutura utilizada pelo parâmetro response_schema do SDK."""
    schema = GeneratedQuestions.model_json_schema()
    assert schema["type"] == "object"
    assert schema["properties"]["questions"]["type"] == "array"
    assert "questions" in schema["required"]
