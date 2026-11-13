"""Modelos de domínio para perguntas de estudo."""

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class QuestionType(StrEnum):
    """Tipos de pergunta suportados pela aplicação."""

    MULTIPLE_CHOICE = "multiple_choice"
    OPEN = "open"


class Question(BaseModel):
    """Representa uma pergunta fundamentada em um material de estudo.

    Attributes:
        type: Tipo da pergunta.
        statement: Enunciado da pergunta.
        answer: Resposta correta.
        explanation: Explicação opcional.
        source_excerpt: Trecho que fundamenta a pergunta.
        options: Alternativas de múltipla escolha, quando aplicável.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    type: QuestionType
    statement: str = Field(min_length=5)
    answer: str = Field(min_length=1)
    explanation: str = ""
    source_excerpt: str = Field(min_length=1)
    options: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_options(self) -> Self:
        """Verifica a compatibilidade entre tipo, alternativas e resposta.

        Returns:
            A pergunta validada.

        Raises:
            ValueError: Quando as alternativas não respeitam as regras do tipo.
        """
        if self.type is QuestionType.MULTIPLE_CHOICE:
            if not 3 <= len(self.options) <= 5:
                raise ValueError("Múltipla escolha exige de 3 a 5 alternativas.")

            if any(not option for option in self.options):
                raise ValueError("Alternativas não podem ser vazias.")

            if len({option.casefold() for option in self.options}) != len(self.options):
                raise ValueError("Alternativas duplicadas não são permitidas.")

            if self.answer not in self.options:
                raise ValueError("A resposta deve corresponder exatamente a uma alternativa.")

        elif self.options:
            raise ValueError("Perguntas abertas não podem ter alternativas.")

        return self


class QuestionSet(BaseModel):
    """Agrupa perguntas validadas geradas a partir de um material.

    Attributes:
        questions: Lista não vazia de perguntas.
    """

    model_config = ConfigDict(extra="forbid")

    questions: list[Question] = Field(min_length=1)
