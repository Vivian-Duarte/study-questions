"""Testes de integração dos componentes iniciais da aplicação."""

from io import BytesIO
from pathlib import Path

import pytest
from reportlab.pdfgen import canvas

from study_questions.config import load_settings
from study_questions.loaders import (
    EmptyDocumentError,
    load_document,
    parse_document,
)
from study_questions.models import Question, QuestionSet, QuestionType


@pytest.mark.parametrize("extension", [".txt", ".md"])
def test_document_to_question_set(
    tmp_path: Path,
    extension: str,
) -> None:
    """Valida o fluxo entre leitura de documento e modelos de domínio.

    Args:
        tmp_path: Diretório temporário criado pelo Pytest.
        extension: Extensão do documento a testar.
    """
    content = "Python é uma linguagem de programação."
    path = tmp_path / f"aula{extension}"
    path.write_text(content, encoding="utf-8")

    extracted = load_document(path)

    question = Question(
        type=QuestionType.OPEN,
        statement="O que é Python?",
        answer="Uma linguagem de programação.",
        source_excerpt=content,
    )

    question_set = QuestionSet(questions=[question])

    restored = QuestionSet.model_validate_json(question_set.model_dump_json())

    assert extracted == content
    assert question.source_excerpt in extracted
    assert restored == question_set


def test_text_upload_with_settings() -> None:
    """Valida a leitura de texto e as configurações da aplicação."""
    settings = load_settings(
        {
            "GEMINI_API_KEY": "fake-test-key",
            "MAX_CHUNK_WORDS": "500",
        }
    )

    content = b"# Introduction to Python"

    extracted = parse_document(
        content,
        "material.md",
    )

    assert extracted == "# Introduction to Python"
    assert settings.max_chunk_words == 500
    assert settings.gemini_api_key == "fake-test-key"


def test_pdf_content_can_be_question_source() -> None:
    """Verifica se texto extraído de PDF pode fundamentar perguntas."""
    buffer = BytesIO()

    pdf = canvas.Canvas(buffer)
    pdf.drawString(
        72,
        720,
        "Python is a programming language.",
    )
    pdf.save()

    extracted = parse_document(
        buffer.getvalue(),
        "material.pdf",
    )

    question = Question(
        type=QuestionType.OPEN,
        statement="What is Python?",
        answer="A programming language.",
        source_excerpt="Python is a programming language.",
    )

    assert question.source_excerpt in extracted


def test_empty_document_stops_processing() -> None:
    """Impede a preparação de perguntas a partir de texto vazio."""
    with pytest.raises(EmptyDocumentError):
        parse_document(b"   ", "material.txt")
