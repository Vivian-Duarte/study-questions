"""Testes finais do fluxo completo do Study Questions."""

import json
from io import BytesIO
from pathlib import Path

import pytest
from reportlab.pdfgen import canvas

from study_questions.config import Settings
from study_questions.exporters import export_anki_tsv, export_json
from study_questions.generation import (
    InsufficientMaterialError,
    InvalidQuestionResponseError,
)
from study_questions.models import QuestionSet, QuestionType
from study_questions.pipeline import generate_from_document


class FakeProvider:
    """Simula respostas de IA para testar o MVP sem internet."""

    def __init__(self, mode: str = "valid") -> None:
        """Define o cenário simulado."""
        self.mode = mode
        self.calls = 0

    def generate(self, *, model: str, prompt: str) -> str:
        """Retorna perguntas baseadas no texto recebido."""
        self.calls += 1

        source_data = json.loads(prompt.split("Material de referência (JSON):\n", 1)[1])
        source_text = str(source_data["text"])

        if self.mode == "empty":
            return json.dumps({"questions": []})

        if self.mode == "invalid_source":
            source_text = "Trecho que não existe no documento."

        questions = [
            {
                "type": "open",
                "statement": "Qual linguagem aparece no material?",
                "answer": "Python",
                "explanation": "O material apresenta Python.",
                "source_excerpt": source_text,
                "options": [],
            },
            {
                "type": "multiple_choice",
                "statement": "Qual linguagem é citada no texto?",
                "answer": "Python",
                "explanation": "Python aparece no documento.",
                "source_excerpt": source_text,
                "options": ["Java", "Python", "Ruby"],
            },
        ]

        return json.dumps(
            {"questions": questions},
            ensure_ascii=False,
        )


def _settings() -> Settings:
    """Cria configurações de teste sem credenciais reais."""
    return Settings(
        gemini_api_key="fake-test-key",
        gemini_model="test-model",
        max_chunk_words=1000,
    )


def _assert_exported_results(result: QuestionSet) -> None:
    """Valida o conjunto e os dois formatos de exportação."""
    assert len(result.questions) == 2

    assert result.questions[0].type == QuestionType.OPEN
    assert result.questions[1].type == QuestionType.MULTIPLE_CHOICE

    json_content = export_json(result)
    restored = QuestionSet.model_validate_json(json_content)

    assert restored == result

    anki_content = export_anki_tsv(result)

    assert anki_content.startswith("#separator:Tab")
    assert "Python" in anki_content
    assert "study_questions open" in anki_content
    assert "study_questions multiple_choice" in anki_content


@pytest.mark.parametrize("extension", [".txt", ".md"])
def test_complete_mvp_with_text_documents(
    tmp_path: Path,
    extension: str,
) -> None:
    """Valida geração e exportação a partir de TXT e Markdown."""
    path = tmp_path / f"material{extension}"
    path.write_text(
        "Python é uma linguagem de programação. Python pode ser utilizada para automação.",
        encoding="utf-8",
    )

    provider = FakeProvider()

    result = generate_from_document(
        path,
        _settings(),
        provider=provider,
        question_count=2,
        overlap_words=0,
    )

    _assert_exported_results(result)

    assert provider.calls == 1


def test_complete_mvp_with_pdf(tmp_path: Path) -> None:
    """Valida o fluxo completo utilizando um documento PDF."""
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)

    pdf.drawString(
        72,
        720,
        "Python is a programming language used for automation.",
    )
    pdf.save()

    path = tmp_path / "material.pdf"
    path.write_bytes(buffer.getvalue())

    provider = FakeProvider()

    result = generate_from_document(
        path,
        _settings(),
        provider=provider,
        question_count=2,
        overlap_words=0,
    )

    _assert_exported_results(result)

    assert provider.calls == 1


def test_rejects_generated_question_without_source(
    tmp_path: Path,
) -> None:
    """Bloqueia perguntas com referências inventadas."""
    path = tmp_path / "material.txt"
    path.write_text(
        "Python é uma linguagem de programação.",
        encoding="utf-8",
    )

    provider = FakeProvider(mode="invalid_source")

    with pytest.raises(
        InvalidQuestionResponseError,
        match="referência ausente",
    ):
        generate_from_document(
            path,
            _settings(),
            provider=provider,
            question_count=2,
        )


def test_handles_insufficient_material(
    tmp_path: Path,
) -> None:
    """Trata documentos que não geram perguntas suficientes."""
    path = tmp_path / "material.txt"
    path.write_text(
        "Conteúdo de estudo.",
        encoding="utf-8",
    )

    provider = FakeProvider(mode="empty")

    with pytest.raises(InsufficientMaterialError):
        generate_from_document(
            path,
            _settings(),
            provider=provider,
            question_count=2,
        )
