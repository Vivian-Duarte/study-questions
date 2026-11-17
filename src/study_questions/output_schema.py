"""Contrato estrutural Pydantic enviado ao Gemini para respostas JSON.

Este contrato é intencionalmente menos restritivo que os modelos de domínio:
permite uma lista vazia e não aplica validações entre alternativas e resposta.
A validação individual de Question continua sendo feita após a resposta,
sem descartar o lote inteiro por causa de uma pergunta inválida.
"""

from pydantic import BaseModel

from study_questions.models import QuestionType


class GeneratedQuestion(BaseModel):
    """Formato esperado para um item gerado pelo modelo de IA."""

    type: QuestionType
    statement: str
    answer: str
    explanation: str
    source_excerpt: str
    options: list[str]


class GeneratedQuestions(BaseModel):
    """Formato da resposta; uma lista vazia representa material insuficiente."""

    questions: list[GeneratedQuestion]
