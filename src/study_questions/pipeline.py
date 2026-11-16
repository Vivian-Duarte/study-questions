"""Orquestração da geração de perguntas para documentos completos."""

from collections.abc import Sequence
from pathlib import Path

from study_questions.chunking import TextChunk, split_text
from study_questions.config import Settings
from study_questions.generation import (
    GeminiTextGenerator,
    InsufficientMaterialError,
    TextGenerationProvider,
    generate_questions,
)
from study_questions.loaders import load_document
from study_questions.models import Question, QuestionSet, QuestionType
from study_questions.prompts import DEFAULT_QUESTION_TYPES, MAX_QUESTIONS_PER_CHUNK

MAX_TOTAL_QUESTIONS = 100


def generate_from_text(
    text: str,
    settings: Settings,
    *,
    provider: TextGenerationProvider | None = None,
    question_count: int = 10,
    question_types: Sequence[QuestionType] = DEFAULT_QUESTION_TYPES,
    overlap_words: int | None = None,
) -> QuestionSet:
    """Gera perguntas sobre um texto completo, distribuindo as solicitações.

    Args:
        text: Conteúdo textual do documento.
        settings: Configurações do projeto.
        provider: Provedor de IA; utiliza Gemini quando omitido.
        question_count: Quantidade máxima de perguntas para o documento.
        question_types: Tipos de perguntas permitidos.
        overlap_words: Sobreposição entre blocos do documento.

    Returns:
        Conjunto validado de perguntas únicas.

    Raises:
        ValueError: Se os parâmetros ou limites forem inválidos.
        InsufficientMaterialError: Se nenhum bloco produzir perguntas.
        GenerationError: Se ocorrer falha na API ou na validação.
    """
    if not 1 <= question_count <= MAX_TOTAL_QUESTIONS:
        raise ValueError("question_count deve estar entre 1 e 100.")

    if not question_types:
        raise ValueError("Informe pelo menos um tipo de pergunta.")

    if any(not isinstance(kind, QuestionType) for kind in question_types):
        raise ValueError("Os tipos de perguntas devem usar QuestionType.")

    if len(set(question_types)) != len(question_types):
        raise ValueError("Os tipos de perguntas não podem se repetir.")

    chunks = split_text(
        text,
        max_words=settings.max_chunk_words,
        overlap_words=overlap_words,
    )
    if not chunks:
        raise InsufficientMaterialError("O documento não contém texto para gerar perguntas.")

    if question_count > len(chunks) * MAX_QUESTIONS_PER_CHUNK:
        raise ValueError("A quantidade solicitada excede o limite de 20 perguntas por bloco.")

    active_provider = (
        provider if provider is not None else GeminiTextGenerator(settings.gemini_api_key)
    )
    unique_questions: list[Question] = []
    seen: set[tuple[QuestionType, str]] = set()

    for chunk, amount in _plan_requests(chunks, question_count):
        try:
            result = generate_questions(
                chunk,
                settings,
                provider=active_provider,
                question_count=amount,
                question_types=question_types,
            )
        except InsufficientMaterialError:
            continue

        for question in result.questions:
            normalized_statement = " ".join(question.statement.casefold().split())
            key = (question.type, normalized_statement)

            if key not in seen:
                seen.add(key)
                unique_questions.append(question)

    if not unique_questions:
        raise InsufficientMaterialError(
            "Nenhum bloco forneceu informações suficientes para gerar perguntas."
        )

    return QuestionSet(questions=unique_questions)


def generate_from_document(
    path: Path,
    settings: Settings,
    *,
    provider: TextGenerationProvider | None = None,
    question_count: int = 10,
    question_types: Sequence[QuestionType] = DEFAULT_QUESTION_TYPES,
    overlap_words: int | None = None,
) -> QuestionSet:
    """Carrega um arquivo e gera perguntas sobre seu conteúdo.

    Args:
        path: Caminho de arquivo TXT, MD ou PDF.
        settings: Configurações do projeto.
        provider: Provedor de IA opcional.
        question_count: Quantidade máxima de perguntas.
        question_types: Tipos de perguntas permitidos.
        overlap_words: Sobreposição entre blocos.

    Returns:
        Conjunto validado de perguntas únicas.
    """
    text = load_document(path)
    return generate_from_text(
        text,
        settings,
        provider=provider,
        question_count=question_count,
        question_types=question_types,
        overlap_words=overlap_words,
    )


def _plan_requests(chunks: list[TextChunk], question_count: int) -> list[tuple[TextChunk, int]]:
    """Distribui a quantidade de perguntas entre blocos do texto.

    Quando há mais blocos que perguntas, seleciona pontos ao longo
    do documento. Caso contrário, distribui as cotas uniformemente.

    Args:
        chunks: Blocos de texto disponíveis, em ordem.
        question_count: Quantidade total desejada.

    Returns:
        Pares de bloco e quantidade de perguntas a solicitar.
    """
    if question_count < len(chunks):
        if question_count == 1:
            return [(chunks[len(chunks) // 2], 1)]

        positions = (
            index * (len(chunks) - 1) // (question_count - 1) for index in range(question_count)
        )
        return [(chunks[position], 1) for position in positions]

    base, remainder = divmod(question_count, len(chunks))
    return [(chunk, base + (1 if index < remainder else 0)) for index, chunk in enumerate(chunks)]
