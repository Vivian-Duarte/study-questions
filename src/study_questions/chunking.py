"""Divisão de textos longos em blocos com sobreposição."""

from dataclasses import dataclass

from study_questions.config import DEFAULT_CHUNK_WORDS


@dataclass(frozen=True, slots=True)
class TextChunk:
    """Representa um bloco extraído de um documento.

    Attributes:
        index: Índice do bloco, começando em zero.
        text: Conteúdo textual do bloco.
        start_word: Posição inicial no texto original.
        end_word: Posição final exclusiva no texto original.
    """

    index: int
    text: str
    start_word: int
    end_word: int


def split_text(
    text: str,
    max_words: int = DEFAULT_CHUNK_WORDS,
    overlap_words: int | None = None,
) -> list[TextChunk]:
    """Divide um texto em blocos de palavras.

    A sobreposição padrão corresponde a 10% do tamanho máximo
    do bloco, arredondada para baixo.

    Args:
        text: Texto original a ser dividido.
        max_words: Quantidade máxima de palavras por bloco.
        overlap_words: Palavras compartilhadas entre blocos.
            Quando None, utiliza 10% de max_words.

    Returns:
        Lista de blocos com texto e posições de origem.

    Raises:
        ValueError: Se os limites de palavras forem inválidos.
    """
    if max_words <= 0:
        raise ValueError("max_words deve ser maior que zero.")

    if overlap_words is None:
        overlap_words = max_words // 10

    if not 0 <= overlap_words < max_words:
        raise ValueError("overlap_words deve estar entre zero e max_words - 1.")

    words = text.split()
    chunks: list[TextChunk] = []
    start = 0

    while start < len(words):
        end = min(start + max_words, len(words))

        chunk = TextChunk(
            index=len(chunks),
            text=" ".join(words[start:end]),
            start_word=start,
            end_word=end,
        )

        chunks.append(chunk)

        if end == len(words):
            break

        start = end - overlap_words

    return chunks
