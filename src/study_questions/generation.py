"""Geração e validação de perguntas utilizando modelos de IA."""

import json
import unicodedata
from collections.abc import Sequence
from types import TracebackType
from typing import Protocol, Self

from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from study_questions.chunking import TextChunk
from study_questions.config import Settings
from study_questions.metrics import GenerationMetrics
from study_questions.models import Question, QuestionSet, QuestionType
from study_questions.output_schema import GeneratedQuestions
from study_questions.prompts import (
    DEFAULT_QUESTION_TYPES,
    build_generation_prompt,
)


class GenerationError(RuntimeError):
    """Representa um erro durante a geração de perguntas."""


class GeminiRequestError(GenerationError):
    """Representa uma falha de comunicação com o Gemini."""


class EmptyResponseError(GenerationError):
    """Indica que o Gemini não retornou conteúdo."""


class InvalidQuestionResponseError(GenerationError):
    """Indica que as perguntas geradas são inválidas."""


class InsufficientMaterialError(GenerationError):
    """Indica que o material não sustenta perguntas válidas."""


class TextGenerationProvider(Protocol):
    """Define o contrato de comunicação com modelos de IA."""

    def generate(self, *, model: str, prompt: str) -> str:
        """Solicita a geração de texto estruturado.

        Args:
            model: Identificador do modelo de IA.
            prompt: Instruções e material de referência.

        Returns:
            Resposta textual produzida pelo modelo.
        """
        ...


class GeminiTextGenerator:
    """Implementa a comunicação com o Gemini."""

    def __init__(self, api_key: str) -> None:
        """Inicializa o provedor.

        Args:
            api_key: Chave de acesso à API.

        Raises:
            ValueError: Se a chave estiver vazia.
        """
        if not api_key.strip():
            raise ValueError("A chave da API não pode estar vazia.")

        self._api_key = api_key
        self._client: genai.Client | None = None

    def __enter__(self) -> Self:
        """Abre um cliente para reutilizá-lo durante uma geração completa."""
        if self._client is not None:
            raise RuntimeError("O cliente Gemini já está aberto.")
        self._client = genai.Client(api_key=self._api_key)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Fecha as conexões mesmo quando a geração falha."""
        client = self._client
        self._client = None
        if client is not None:
            client.close()

    def generate(self, *, model: str, prompt: str) -> str:
        """Envia um prompt ao Gemini e recupera sua resposta.

        Args:
            model: Modelo Gemini a utilizar.
            prompt: Prompt preparado para geração.

        Returns:
            Resposta JSON em formato de texto.

        Raises:
            GeminiRequestError: Se a API retornar um erro.
            EmptyResponseError: Se não houver conteúdo textual.
        """
        try:
            if self._client is None:
                # Uso isolado: preserva o fechamento automático por chamada.
                with genai.Client(api_key=self._api_key) as client:
                    content = self._request_content(client, model=model, prompt=prompt)
            else:
                # Uso pelo pipeline: reaproveita a conexão entre blocos.
                content = self._request_content(self._client, model=model, prompt=prompt)

        except errors.APIError as exc:
            raise GeminiRequestError(
                "Falha na solicitação ao Gemini. "
                "Verifique as credenciais, o modelo e os limites da API."
            ) from exc

        if content is None or not content.strip():
            raise EmptyResponseError("O Gemini não retornou conteúdo textual.")

        return content

    @staticmethod
    def _request_content(client: genai.Client, *, model: str, prompt: str) -> str | None:
        """Solicita JSON estruturado pelo esquema Pydantic, sem novas chamadas."""
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GeneratedQuestions,
            ),
        )
        return response.text


def generate_questions(
    chunk: TextChunk,
    settings: Settings,
    *,
    provider: TextGenerationProvider | None = None,
    question_count: int = 5,
    question_types: Sequence[QuestionType] = DEFAULT_QUESTION_TYPES,
    metrics: GenerationMetrics | None = None,
) -> QuestionSet:
    """Gera e valida perguntas com base em um bloco de texto.

    Args:
        chunk: Bloco contendo o material de estudo.
        settings: Configurações da aplicação.
        provider: Provedor de IA. Se None, utiliza Gemini.
        question_count: Número máximo de perguntas solicitadas.
        question_types: Tipos de perguntas permitidos.
        metrics: Diagnóstico opcional, sem conteúdo das perguntas.

    Returns:
        Conjunto de perguntas validado pelo Pydantic.

    Raises:
        ValueError: Se os parâmetros forem inválidos.
        GenerationError: Se a geração ou validação falhar.
    """
    prompt = build_generation_prompt(
        chunk,
        question_count=question_count,
        question_types=question_types,
    )

    if metrics is not None:
        metrics.questions_requested += question_count

    if provider is None:
        provider = GeminiTextGenerator(settings.gemini_api_key)

    raw_response = provider.generate(
        model=settings.gemini_model,
        prompt=prompt,
    )

    return _validate_generated_questions(
        raw_response,
        chunk=chunk,
        question_count=question_count,
        question_types=question_types,
        metrics=metrics,
    )


def _validate_generated_questions(
    raw_response: str,
    *,
    chunk: TextChunk,
    question_count: int,
    question_types: Sequence[QuestionType],
    metrics: GenerationMetrics | None = None,
) -> QuestionSet:
    """Valida a estrutura e as referências das perguntas.

    Args:
        raw_response: Resposta textual do provedor.
        chunk: Bloco utilizado como referência.
        question_count: Quantidade máxima permitida.
        question_types: Tipos de perguntas permitidos.
        metrics: Coletor opcional dos motivos de descarte.

    Returns:
        Conjunto validado de perguntas.

    Raises:
        InvalidQuestionResponseError: Se a resposta for inválida.
        InsufficientMaterialError: Se nenhuma pergunta for gerada.
    """
    try:
        payload: object = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        if metrics is not None:
            metrics.responses_invalid_json += 1
        raise InvalidQuestionResponseError("O modelo retornou um JSON inválido.") from exc

    if (
        not isinstance(payload, dict)
        or set(payload) != {"questions"}
        or not isinstance(payload["questions"], list)
    ):
        if metrics is not None:
            metrics.responses_invalid_format += 1
        raise InvalidQuestionResponseError("As perguntas não respeitam o modelo de dados.")

    raw_questions = payload["questions"]
    if metrics is not None:
        metrics.questions_received += len(raw_questions)
        if len(raw_questions) <= question_count:
            metrics.questions_missing_from_response += question_count - len(raw_questions)

    if not raw_questions:
        if metrics is not None:
            metrics.responses_empty += 1
        raise InsufficientMaterialError(
            "O material não contém informações suficientes para gerar perguntas válidas."
        )

    if len(raw_questions) > question_count:
        if metrics is not None:
            metrics.responses_excess += 1
            metrics.questions_rejected_excess_response += len(raw_questions)
        raise InvalidQuestionResponseError("O modelo gerou mais perguntas do que o solicitado.")

    verified_questions: list[Question] = []
    normalized_source = _normalize_reference(chunk.text)
    has_invalid_reference = False

    for raw_question in raw_questions:
        try:
            question = Question.model_validate(raw_question)
        except ValidationError:
            if metrics is not None:
                metrics.questions_rejected_structure += 1
            continue

        if question.type not in question_types:
            if metrics is not None:
                metrics.questions_rejected_type += 1
            continue

        normalized_excerpt = _normalize_reference(question.source_excerpt)
        if normalized_excerpt not in normalized_source:
            has_invalid_reference = True
            if metrics is not None:
                metrics.questions_rejected_reference += 1
            continue

        verified_questions.append(question)

    if not verified_questions:
        if has_invalid_reference:
            raise InvalidQuestionResponseError(
                "Uma pergunta possui uma referência ausente do documento original."
            )
        raise InvalidQuestionResponseError("As perguntas não respeitam o modelo de dados.")

    return QuestionSet(questions=verified_questions)


def _normalize_reference(text: str) -> str:
    """Normaliza texto para verificar referências documentais.

    Args:
        text: Texto ou citação a normalizar.

    Returns:
        Texto com espaços uniformizados e Unicode normalizado.
    """
    normalized = unicodedata.normalize("NFKC", text)
    return " ".join(normalized.split()).casefold()
