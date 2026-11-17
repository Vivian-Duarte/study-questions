"""Testes de geração e validação de perguntas."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest
from google.genai import errors

from study_questions.chunking import split_text
from study_questions.config import Settings, load_settings
from study_questions.generation import (
    EmptyResponseError,
    GeminiRequestError,
    GeminiTextGenerator,
    InsufficientMaterialError,
    InvalidQuestionResponseError,
    generate_questions,
)
from study_questions.models import QuestionType

SOURCE_TEXT = "Python é uma linguagem de programação. A sintaxe de Python é simples."
SOURCE_EXCERPT = "Python é uma linguagem de programação."


class FakeGenerator:
    """Simula um provedor de IA sem acessar a internet."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[tuple[str, str]] = []

    def generate(self, *, model: str, prompt: str) -> str:
        """Registra a solicitação e retorna uma resposta fictícia."""
        self.calls.append((model, prompt))
        return self.response


def _settings() -> Settings:
    """Cria configurações de teste."""
    return load_settings(
        {
            "GEMINI_API_KEY": "fake-test-key",
            "GEMINI_MODEL": "gemini-3.5-flash-lite",
        }
    )


def _chunk():
    """Cria um bloco de referência para os testes."""
    return split_text(
        SOURCE_TEXT,
        max_words=100,
        overlap_words=0,
    )[0]


def _open_question() -> dict[str, object]:
    """Cria uma pergunta discursiva válida."""
    return {
        "type": "open",
        "statement": "O que é Python?",
        "answer": "Uma linguagem de programação.",
        "explanation": "O texto define Python como uma linguagem.",
        "source_excerpt": SOURCE_EXCERPT,
        "options": [],
    }


def _multiple_choice_question() -> dict[str, object]:
    """Cria uma pergunta de múltipla escolha válida."""
    return {
        "type": "multiple_choice",
        "statement": "Qual linguagem é citada no texto?",
        "answer": "Python",
        "explanation": "Python é mencionada no material.",
        "source_excerpt": SOURCE_EXCERPT,
        "options": ["Python", "Java", "Ruby"],
    }


def _response(questions: list[dict[str, object]]) -> str:
    """Serializa perguntas fictícias para JSON."""
    return json.dumps(
        {"questions": questions},
        ensure_ascii=False,
    )


def test_generates_valid_open_question() -> None:
    """Converte uma resposta simulada em QuestionSet."""
    provider = FakeGenerator(_response([_open_question()]))

    result = generate_questions(
        _chunk(),
        _settings(),
        provider=provider,
        question_count=1,
        question_types=(QuestionType.OPEN,),
    )

    assert len(result.questions) == 1
    assert result.questions[0].answer == ("Uma linguagem de programação.")
    assert len(provider.calls) == 1
    assert provider.calls[0][0] == "gemini-3.5-flash-lite"
    assert "Gere até 1 perguntas" in provider.calls[0][1]


def test_generates_multiple_choice_question() -> None:
    """Aceita perguntas objetivas com alternativas válidas."""
    provider = FakeGenerator(_response([_multiple_choice_question()]))

    result = generate_questions(
        _chunk(),
        _settings(),
        provider=provider,
        question_types=(QuestionType.MULTIPLE_CHOICE,),
    )

    assert result.questions[0].answer == "Python"
    assert len(result.questions[0].options) == 3


def test_accepts_fewer_questions_than_requested() -> None:
    """Permite gerar menos perguntas quando o conteúdo é limitado."""
    provider = FakeGenerator(_response([_open_question()]))

    result = generate_questions(
        _chunk(),
        _settings(),
        provider=provider,
        question_count=5,
    )

    assert len(result.questions) == 1


def test_rejects_invalid_json() -> None:
    """Rejeita respostas que não são JSON válido."""
    provider = FakeGenerator("not a json response")

    with pytest.raises(InvalidQuestionResponseError):
        generate_questions(
            _chunk(),
            _settings(),
            provider=provider,
        )


def test_rejects_invalid_question_structure() -> None:
    """Rejeita perguntas sem os campos obrigatórios."""
    provider = FakeGenerator(_response([{"type": "open"}]))

    with pytest.raises(InvalidQuestionResponseError):
        generate_questions(
            _chunk(),
            _settings(),
            provider=provider,
        )


def test_rejects_invalid_json_root() -> None:
    """Rejeita respostas cuja raiz não é um objeto válido."""
    provider = FakeGenerator("null")

    with pytest.raises(InvalidQuestionResponseError):
        generate_questions(
            _chunk(),
            _settings(),
            provider=provider,
        )


def test_rejects_empty_question_list() -> None:
    """Identifica material insuficiente para gerar perguntas."""
    provider = FakeGenerator(_response([]))

    with pytest.raises(InsufficientMaterialError):
        generate_questions(
            _chunk(),
            _settings(),
            provider=provider,
        )


def test_rejects_missing_source_excerpt() -> None:
    """Rejeita referências não presentes no material."""
    question = _open_question()
    question["source_excerpt"] = "Informação inventada."

    provider = FakeGenerator(_response([question]))

    with pytest.raises(
        InvalidQuestionResponseError,
        match="referência ausente",
    ):
        generate_questions(
            _chunk(),
            _settings(),
            provider=provider,
        )


def test_rejects_unrequested_question_type() -> None:
    """Rejeita perguntas de tipos não solicitados."""
    provider = FakeGenerator(_response([_multiple_choice_question()]))

    with pytest.raises(InvalidQuestionResponseError):
        generate_questions(
            _chunk(),
            _settings(),
            provider=provider,
            question_types=(QuestionType.OPEN,),
        )


def test_rejects_excess_questions() -> None:
    """Respeita a quantidade máxima de perguntas."""
    provider = FakeGenerator(_response([_open_question(), _open_question()]))

    with pytest.raises(InvalidQuestionResponseError):
        generate_questions(
            _chunk(),
            _settings(),
            provider=provider,
            question_count=1,
        )


def test_rejects_invalid_parameters_before_api_call() -> None:
    """Não chama o provedor quando o prompt é inválido."""
    provider = FakeGenerator(_response([_open_question()]))

    with pytest.raises(ValueError):
        generate_questions(
            _chunk(),
            _settings(),
            provider=provider,
            question_count=0,
        )

    assert provider.calls == []


def test_gemini_rejects_blank_api_key() -> None:
    """Impede a criação de um provedor sem credenciais."""
    with pytest.raises(ValueError):
        GeminiTextGenerator("  ")


def test_gemini_uses_json_response_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Confirma a configuração da SDK sem chamadas reais."""
    fake_client = MagicMock()
    fake_client.__enter__.return_value.models.generate_content.return_value = SimpleNamespace(
        text='{"questions": []}'
    )

    factory = Mock(return_value=fake_client)

    monkeypatch.setattr(
        "study_questions.generation.genai.Client",
        factory,
    )

    generator = GeminiTextGenerator("fake-test-key")

    result = generator.generate(
        model="test-model",
        prompt="test-prompt",
    )

    assert result == '{"questions": []}'
    factory.assert_called_once_with(api_key="fake-test-key")

    call = fake_client.__enter__.return_value.models.generate_content.call_args

    assert call.kwargs["model"] == "test-model"
    assert call.kwargs["contents"] == "test-prompt"
    assert call.kwargs["config"].response_mime_type == ("application/json")
    fake_client.__exit__.assert_called_once()


def test_gemini_rejects_empty_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Detecta respostas sem conteúdo textual."""
    fake_client = MagicMock()
    fake_client.__enter__.return_value.models.generate_content.return_value = SimpleNamespace(
        text=None
    )

    monkeypatch.setattr(
        "study_questions.generation.genai.Client",
        Mock(return_value=fake_client),
    )

    generator = GeminiTextGenerator("fake-test-key")

    with pytest.raises(EmptyResponseError):
        generator.generate(
            model="test-model",
            prompt="test-prompt",
        )


def test_gemini_wraps_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Converte falhas da API em erros da aplicação."""
    fake_client = MagicMock()

    fake_client.__enter__.return_value.models.generate_content.side_effect = errors.APIError(
        429,
        {"error": {"message": "Limite de requisições"}},
    )

    monkeypatch.setattr(
        "study_questions.generation.genai.Client",
        Mock(return_value=fake_client),
    )

    generator = GeminiTextGenerator("fake-test-key")

    with pytest.raises(GeminiRequestError):
        generator.generate(
            model="test-model",
            prompt="test-prompt",
        )


def test_accepts_reference_with_different_whitespace() -> None:
    """Aceita citações com espaços e quebras de linha diferentes."""
    question = _open_question()
    question["source_excerpt"] = "PYTHON   é\numa linguagem de programação."

    provider = FakeGenerator(_response([question]))

    result = generate_questions(
        _chunk(),
        _settings(),
        provider=provider,
    )

    assert len(result.questions) == 1


def test_discards_question_with_unverifiable_reference() -> None:
    """Preserva perguntas válidas e descarta citações inventadas."""
    valid_question = _open_question()
    invalid_question = _open_question()

    invalid_question["statement"] = "Qual linguagem é apresentada no documento?"
    invalid_question["source_excerpt"] = "Essa frase não existe no documento."

    provider = FakeGenerator(_response([valid_question, invalid_question]))

    result = generate_questions(
        _chunk(),
        _settings(),
        provider=provider,
        question_count=2,
    )

    assert len(result.questions) == 1
    assert result.questions[0].statement == ("O que é Python?")


def test_preserves_valid_question_when_another_has_invalid_structure() -> None:
    """Aproveita perguntas corretas mesmo com outras malformadas."""
    provider = FakeGenerator(_response([_open_question(), {"type": "open"}]))

    result = generate_questions(
        _chunk(),
        _settings(),
        provider=provider,
        question_count=2,
    )

    assert len(result.questions) == 1
    assert result.questions[0].statement == "O que é Python?"
    assert len(provider.calls) == 1


def test_rejects_unexpected_json_root_fields() -> None:
    """Mantém o contrato estrito do JSON recebido."""
    provider = FakeGenerator(
        json.dumps({"questions": [_open_question()], "metadata": "inesperado"})
    )

    with pytest.raises(InvalidQuestionResponseError, match="modelo de dados"):
        generate_questions(_chunk(), _settings(), provider=provider)


def test_preserves_valid_question_with_unrequested_question_type() -> None:
    """Não descarta perguntas válidas por causa de um tipo não solicitado."""
    provider = FakeGenerator(_response([_open_question(), _multiple_choice_question()]))

    result = generate_questions(
        _chunk(),
        _settings(),
        provider=provider,
        question_count=2,
        question_types=(QuestionType.OPEN,),
    )

    assert len(result.questions) == 1
    assert result.questions[0].type == QuestionType.OPEN


def test_gemini_reuses_single_client_in_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Utiliza um cliente para várias requisições e fecha ao terminar."""
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = SimpleNamespace(text='{"questions": []}')
    factory = Mock(return_value=fake_client)
    monkeypatch.setattr("study_questions.generation.genai.Client", factory)

    with GeminiTextGenerator("fake-test-key") as generator:
        first = generator.generate(model="test-model", prompt="chunk 1")
        second = generator.generate(model="test-model", prompt="chunk 2")

    assert first == second == '{"questions": []}'
    factory.assert_called_once_with(api_key="fake-test-key")
    assert fake_client.models.generate_content.call_count == 2
    fake_client.close.assert_called_once()


def test_gemini_closes_client_when_provider_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Libera conexões quando uma chamada ao Gemini falha."""
    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = errors.APIError(
        429,
        {"error": {"message": "Limite de requisições"}},
    )
    monkeypatch.setattr("study_questions.generation.genai.Client", Mock(return_value=fake_client))

    with pytest.raises(GeminiRequestError):
        with GeminiTextGenerator("fake-test-key") as generator:
            generator.generate(model="test-model", prompt="test-prompt")

    fake_client.close.assert_called_once()


def test_diagnostics_distinguish_structure_type_and_reference_rejections() -> None:
    """Contabiliza cada descarte sem perder as perguntas aproveitáveis."""
    from study_questions.metrics import GenerationMetrics

    wrong_type = _multiple_choice_question()
    bad_reference = _open_question()
    bad_reference["statement"] = "Qual a principal linguagem?"
    bad_reference["source_excerpt"] = "Citação inexistente no material."

    provider = FakeGenerator(
        _response([_open_question(), {"type": "open"}, wrong_type, bad_reference])
    )
    metrics = GenerationMetrics()
    result = generate_questions(
        _chunk(),
        _settings(),
        provider=provider,
        question_count=4,
        question_types=(QuestionType.OPEN,),
        metrics=metrics,
    )

    assert len(result.questions) == 1
    assert len(provider.calls) == 1
    assert metrics.questions_requested == 4
    assert metrics.questions_received == 4
    assert metrics.questions_missing_from_response == 0
    assert metrics.questions_rejected_structure == 1
    assert metrics.questions_rejected_type == 1
    assert metrics.questions_rejected_reference == 1
    assert metrics.responses_invalid_json == 0
    assert metrics.responses_invalid_format == 0


def test_diagnostics_count_missing_questions_without_treating_them_as_discards() -> None:
    """O que o Gemini não entregou não deve ser contado como rejeição."""
    from study_questions.metrics import GenerationMetrics

    provider = FakeGenerator(_response([_open_question()]))
    metrics = GenerationMetrics()
    result = generate_questions(
        _chunk(), _settings(), provider=provider, question_count=5, metrics=metrics
    )

    assert len(result.questions) == 1
    assert len(provider.calls) == 1
    assert metrics.questions_requested == 5
    assert metrics.questions_received == 1
    assert metrics.questions_missing_from_response == 4
    assert metrics.questions_rejected_structure == 0
    assert metrics.questions_rejected_type == 0
    assert metrics.questions_rejected_reference == 0


@pytest.mark.parametrize(
    ("response", "expected_field"),
    [
        ("não é JSON", "responses_invalid_json"),
        (json.dumps({"questions": "não é lista"}), "responses_invalid_format"),
        (_response([]), "responses_empty"),
        (_response([_open_question(), _open_question()]), "responses_excess"),
    ],
)
def test_diagnostics_record_rejected_response_reasons(response: str, expected_field: str) -> None:
    """Registra falhas no nível de resposta mesmo quando uma exceção é lançada."""
    from study_questions.metrics import GenerationMetrics

    provider = FakeGenerator(response)
    metrics = GenerationMetrics()
    with pytest.raises((InvalidQuestionResponseError, InsufficientMaterialError)):
        generate_questions(
            _chunk(), _settings(), provider=provider, question_count=1, metrics=metrics
        )

    assert len(provider.calls) == 1
    assert metrics.questions_requested == 1
    assert getattr(metrics, expected_field) == 1

    if expected_field == "responses_excess":
        # A resposta inteira, não apenas o excedente, é rejeitada atualmente.
        assert metrics.questions_received == 2
        assert metrics.questions_rejected_excess_response == 2
    elif expected_field == "responses_empty":
        assert metrics.questions_received == 0
        assert metrics.questions_missing_from_response == 1
    else:
        assert metrics.questions_received == 0
        assert metrics.questions_missing_from_response == 0


def test_diagnostics_record_failed_validation_when_all_questions_are_rejected() -> None:
    """Mantém contadores de validação mesmo após a exceção final."""
    from study_questions.metrics import GenerationMetrics

    provider = FakeGenerator(_response([{"type": "open"}]))
    metrics = GenerationMetrics()
    with pytest.raises(InvalidQuestionResponseError):
        generate_questions(
            _chunk(), _settings(), provider=provider, question_count=1, metrics=metrics
        )

    assert metrics.questions_received == 1
    assert metrics.questions_rejected_structure == 1
    assert metrics.questions_missing_from_response == 0


def test_diagnostics_only_contain_aggregated_counts() -> None:
    """Não retém o texto do usuário ou a chave do provedor nas métricas."""
    from dataclasses import asdict

    from study_questions.metrics import GenerationMetrics

    metrics = GenerationMetrics()
    generate_questions(
        _chunk(),
        _settings(),
        provider=FakeGenerator(_response([_open_question()])),
        question_count=1,
        metrics=metrics,
    )
    serialized = str(asdict(metrics))
    assert SOURCE_EXCERPT not in serialized
    assert "fake-test-key" not in serialized
