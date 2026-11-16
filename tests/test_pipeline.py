"""Testes da geração de perguntas a partir de documentos completos."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from study_questions.config import Settings, load_settings
from study_questions.generation import GeminiRequestError, InsufficientMaterialError
from study_questions.models import QuestionType
from study_questions.pipeline import generate_from_document, generate_from_text

SOURCE_TEXT = "alfa bravo charlie delta echo foxtrot golf hotel india juliet kilo lima"


class FakeProvider:
    """Simula o provedor e registra solicitações sem usar a internet."""

    def __init__(
        self,
        *,
        insufficient: set[int] | None = None,
        max_per_call: int | None = None,
        repeated_statement: bool = False,
        fail_at: int | None = None,
    ) -> None:
        self.insufficient = insufficient or set()
        self.max_per_call = max_per_call
        self.repeated_statement = repeated_statement
        self.fail_at = fail_at
        self.calls: list[tuple[int, int, str]] = []

    def generate(self, *, model: str, prompt: str) -> str:
        """Produz respostas válidas para cada bloco solicitado."""
        reference = json.loads(prompt.split("Material de referência (JSON):\n", 1)[1])
        index = int(reference["chunk_index"])
        request_line = next(line for line in prompt.splitlines() if line.startswith("Gere até "))
        requested = int(request_line.split()[2])
        self.calls.append((index, requested, model))

        if index == self.fail_at:
            raise GeminiRequestError("Falha simulada de comunicação.")

        if index in self.insufficient:
            return json.dumps({"questions": []})

        amount = min(requested, self.max_per_call or requested)
        questions = []
        for number in range(amount):
            statement = (
                "Que conteúdo aparece no documento?"
                if self.repeated_statement
                else f"Qual o conteúdo do bloco {index}, pergunta {number}?"
            )
            questions.append(
                {
                    "type": "open",
                    "statement": statement,
                    "answer": "O conteúdo informado no texto.",
                    "explanation": "Resposta com base no material.",
                    "source_excerpt": reference["text"],
                    "options": [],
                }
            )
        return json.dumps({"questions": questions}, ensure_ascii=False)


def _settings() -> Settings:
    """Fornece configurações isoladas para os testes."""
    return load_settings(
        {
            "GEMINI_API_KEY": "fake-api-key",
            "GEMINI_MODEL": "test-model",
            "MAX_CHUNK_WORDS": "4",
        }
    )


def test_distributes_questions_between_chunks() -> None:
    """Distribui cinco perguntas pelos três blocos disponíveis."""
    provider = FakeProvider()

    result = generate_from_text(
        SOURCE_TEXT,
        _settings(),
        provider=provider,
        question_count=5,
        overlap_words=0,
    )

    assert len(result.questions) == 5
    assert provider.calls == [
        (0, 2, "test-model"),
        (1, 2, "test-model"),
        (2, 1, "test-model"),
    ]
    assert all(q.source_excerpt in SOURCE_TEXT for q in result.questions)


def test_selects_distant_chunks_for_few_questions() -> None:
    """Seleciona o começo e o fim quando há mais blocos que perguntas."""
    provider = FakeProvider()
    document = " ".join(f"palavra{i}" for i in range(16))

    result = generate_from_text(
        document,
        _settings(),
        provider=provider,
        question_count=2,
        overlap_words=0,
    )

    assert len(result.questions) == 2
    assert [index for index, _, _ in provider.calls] == [0, 3]


def test_selects_middle_chunk_for_single_question() -> None:
    """Escolhe o bloco central para uma única pergunta."""
    provider = FakeProvider()

    result = generate_from_text(
        SOURCE_TEXT,
        _settings(),
        provider=provider,
        question_count=1,
        overlap_words=0,
    )

    assert len(result.questions) == 1
    assert provider.calls == [(1, 1, "test-model")]


def test_skips_chunks_with_insufficient_material() -> None:
    """Continua a geração quando um bloco não produz perguntas."""
    provider = FakeProvider(insufficient={1})

    result = generate_from_text(
        SOURCE_TEXT,
        _settings(),
        provider=provider,
        question_count=3,
        overlap_words=0,
    )

    assert len(result.questions) == 2
    assert len(provider.calls) == 3


def test_raises_if_all_chunks_are_insufficient() -> None:
    """Sinaliza quando nenhum bloco produz perguntas."""
    provider = FakeProvider(insufficient={0, 1, 2})

    with pytest.raises(InsufficientMaterialError):
        generate_from_text(
            SOURCE_TEXT,
            _settings(),
            provider=provider,
            question_count=3,
            overlap_words=0,
        )


def test_removes_duplicate_questions_across_chunks() -> None:
    """Remove perguntas com o mesmo tipo e enunciado."""
    provider = FakeProvider(repeated_statement=True)

    result = generate_from_text(
        SOURCE_TEXT,
        _settings(),
        provider=provider,
        question_count=3,
        overlap_words=0,
    )

    assert len(result.questions) == 1
    assert len(provider.calls) == 3


def test_accepts_fewer_questions_than_requested() -> None:
    """Aceita respostas menores sem fazer novas solicitações."""
    provider = FakeProvider(max_per_call=1)

    result = generate_from_text(
        SOURCE_TEXT,
        _settings(),
        provider=provider,
        question_count=5,
        overlap_words=0,
    )

    assert len(result.questions) == 3
    assert len(provider.calls) == 3


def test_generates_from_markdown_file(tmp_path: Path) -> None:
    """Integra leitura do arquivo e geração de perguntas."""
    path = tmp_path / "aula.md"
    path.write_text(SOURCE_TEXT, encoding="utf-8")
    provider = FakeProvider()

    result = generate_from_document(
        path,
        _settings(),
        provider=provider,
        question_count=2,
        overlap_words=0,
    )

    assert len(result.questions) == 2
    assert len(provider.calls) == 2


def test_propagates_missing_file_error(tmp_path: Path) -> None:
    """Não oculta erros de arquivo inexistente."""
    provider = FakeProvider()

    with pytest.raises(FileNotFoundError):
        generate_from_document(
            tmp_path / "inexistente.txt",
            _settings(),
            provider=provider,
        )

    assert provider.calls == []


def test_rejects_empty_text_before_api_call() -> None:
    """Não chama a API quando o documento está vazio."""
    provider = FakeProvider()

    with pytest.raises(InsufficientMaterialError):
        generate_from_text(" \n ", _settings(), provider=provider)

    assert provider.calls == []


@pytest.mark.parametrize("count", [0, -1, 101])
def test_rejects_invalid_question_count(count: int) -> None:
    """Rejeita quantidades fora do intervalo permitido."""
    provider = FakeProvider()

    with pytest.raises(ValueError, match="question_count"):
        generate_from_text(
            SOURCE_TEXT,
            _settings(),
            provider=provider,
            question_count=count,
        )

    assert provider.calls == []


def test_rejects_more_than_twenty_per_chunk() -> None:
    """Evita solicitar mais de vinte perguntas de um único bloco."""
    with pytest.raises(ValueError, match="20 perguntas por bloco"):
        generate_from_text(
            "alfa beta",
            _settings(),
            provider=FakeProvider(),
            question_count=21,
        )


def test_rejects_invalid_overlap() -> None:
    """Encaminha limites inválidos para o validador de chunking."""
    with pytest.raises(ValueError, match="overlap_words"):
        generate_from_text(
            SOURCE_TEXT,
            _settings(),
            provider=FakeProvider(),
            overlap_words=4,
        )


def test_rejects_empty_question_types() -> None:
    """Rejeita gerações sem tipo de pergunta permitido."""
    with pytest.raises(ValueError, match="pelo menos um tipo"):
        generate_from_text(
            SOURCE_TEXT,
            _settings(),
            provider=FakeProvider(),
            question_types=(),
        )


def test_rejects_duplicate_question_types() -> None:
    """Rejeita tipos repetidos antes de solicitar a IA."""
    with pytest.raises(ValueError, match="não podem se repetir"):
        generate_from_text(
            SOURCE_TEXT,
            _settings(),
            provider=FakeProvider(),
            question_types=(QuestionType.OPEN, QuestionType.OPEN),
        )


def test_uses_gemini_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cria um provedor padrão uma vez, sem executar uma API real."""
    fake_provider = FakeProvider()
    factory = Mock(return_value=fake_provider)
    monkeypatch.setattr("study_questions.pipeline.GeminiTextGenerator", factory)

    result = generate_from_text(
        SOURCE_TEXT,
        _settings(),
        question_count=2,
        overlap_words=0,
    )

    assert len(result.questions) == 2
    factory.assert_called_once_with("fake-api-key")


def test_propagates_provider_failures() -> None:
    """Não trata falha de rede como insuficiência de material."""
    provider = FakeProvider(fail_at=0)

    with pytest.raises(GeminiRequestError):
        generate_from_text(
            SOURCE_TEXT,
            _settings(),
            provider=provider,
            question_count=3,
            overlap_words=0,
        )


def test_rejects_invalid_question_type() -> None:
    """Rejeita tipos que não pertencem ao enum de domínio."""
    with pytest.raises(ValueError, match="QuestionType"):
        generate_from_text(
            SOURCE_TEXT,
            _settings(),
            provider=FakeProvider(),
            question_types=("invalid",),  # type: ignore[arg-type]
        )
