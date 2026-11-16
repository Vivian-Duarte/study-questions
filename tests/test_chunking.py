"""Testes do algoritmo de divisão de textos."""

import pytest

from study_questions.chunking import split_text
from study_questions.config import load_settings
from study_questions.loaders import parse_document


@pytest.mark.parametrize("text", ["", " \n\t "])
def test_returns_no_chunks_for_blank_text(text: str) -> None:
    """Retorna uma lista vazia para textos sem palavras."""
    assert split_text(text) == []


def test_returns_single_chunk_for_short_text() -> None:
    """Mantém textos curtos em um único bloco."""
    chunks = split_text("Python é uma linguagem.")

    assert len(chunks) == 1
    assert chunks[0].text == "Python é uma linguagem."
    assert chunks[0].index == 0
    assert chunks[0].start_word == 0
    assert chunks[0].end_word == 4


def test_accepts_text_at_exact_word_limit() -> None:
    """Não cria outro bloco quando o limite é exato."""
    chunks = split_text(
        "um dois três quatro",
        max_words=4,
    )

    assert len(chunks) == 1
    assert chunks[0].end_word == 4


def test_splits_text_without_overlap() -> None:
    """Divide textos sem repetir palavras."""
    chunks = split_text(
        "um dois tres quatro cinco seis sete",
        max_words=3,
        overlap_words=0,
    )

    assert [chunk.text for chunk in chunks] == [
        "um dois tres",
        "quatro cinco seis",
        "sete",
    ]

    assert [(chunk.start_word, chunk.end_word) for chunk in chunks] == [
        (0, 3),
        (3, 6),
        (6, 7),
    ]

    assert [chunk.index for chunk in chunks] == [0, 1, 2]


def test_splits_text_with_overlap() -> None:
    """Compartilha palavras entre blocos consecutivos."""
    chunks = split_text(
        "um dois tres quatro cinco seis sete oito nove",
        max_words=4,
        overlap_words=1,
    )

    assert [chunk.text for chunk in chunks] == [
        "um dois tres quatro",
        "quatro cinco seis sete",
        "sete oito nove",
    ]


def test_uses_default_ten_percent_overlap() -> None:
    """Calcula automaticamente a sobreposição padrão."""
    text = " ".join(f"w{i}" for i in range(12))

    chunks = split_text(text, max_words=10)

    assert len(chunks) == 2
    assert chunks[0].start_word == 0
    assert chunks[0].end_word == 10
    assert chunks[1].start_word == 9
    assert chunks[1].end_word == 12


def test_handles_large_overlap_without_extra_chunk() -> None:
    """Evita gerar um bloco final somente com repetição."""
    chunks = split_text(
        "a b c d e",
        max_words=4,
        overlap_words=3,
    )

    assert [chunk.text for chunk in chunks] == [
        "a b c d",
        "b c d e",
    ]


def test_normalizes_whitespace() -> None:
    """Normaliza espaços e quebras de linha no conteúdo."""
    chunks = split_text("  Python\té\n uma   linguagem. \n")

    assert chunks[0].text == "Python é uma linguagem."


def test_preserves_unicode() -> None:
    """Mantém caracteres acentuados e Unicode."""
    chunks = split_text("ação ciência 🤖")

    assert chunks[0].text == "ação ciência 🤖"


@pytest.mark.parametrize(
    ("max_words", "overlap_words"),
    [
        (0, None),
        (-2, None),
        (3, -1),
        (3, 3),
        (3, 4),
    ],
)
def test_rejects_invalid_parameters(
    max_words: int,
    overlap_words: int | None,
) -> None:
    """Rejeita limites de palavras inválidos."""
    with pytest.raises(ValueError):
        split_text(
            "documento de teste",
            max_words=max_words,
            overlap_words=overlap_words,
        )


def test_works_with_document_and_settings() -> None:
    """Integra o chunking com o carregador e as configurações."""
    settings = load_settings(
        {
            "GEMINI_API_KEY": "fake-test-key",
            "MAX_CHUNK_WORDS": "4",
        }
    )

    text = parse_document(
        b"Python facilita analise de dados e automacao",
        "aula.txt",
    )

    chunks = split_text(
        text,
        max_words=settings.max_chunk_words,
        overlap_words=1,
    )

    assert [chunk.text for chunk in chunks] == [
        "Python facilita analise de",
        "de dados e automacao",
    ]
