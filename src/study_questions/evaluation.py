"""Avaliação offline e determinística de perguntas geradas.

Métricas lexicais não verificam, por si só, veracidade ou fidelidade semântica.
A avaliação não chama provedores de IA nem armazena dados de geração.
"""

import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from study_questions.models import Question, QuestionType


class EvaluationCase(BaseModel):
    """Caso anotado com o material, candidatas e respostas de referência."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(min_length=1)
    source_text: str = Field(min_length=1)
    questions: list[Any] = Field(default_factory=list)
    expected_answers: list[str | None] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_reference_alignment(self) -> "EvaluationCase":
        """Exige uma anotação por pergunta quando há respostas de referência."""
        if self.expected_answers and len(self.expected_answers) != len(self.questions):
            raise ValueError("expected_answers deve ter o mesmo tamanho de questions.")
        if any(answer is not None and not answer.strip() for answer in self.expected_answers):
            raise ValueError("Respostas de referência não podem ser vazias.")
        return self


class EvaluationDataset(BaseModel):
    """Conjunto de casos auditáveis, com identificadores estáveis."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1, le=1)
    cases: list[EvaluationCase] = Field(min_length=1)

    @model_validator(mode="after")
    def check_unique_ids(self) -> "EvaluationDataset":
        """Rejeita identificadores duplicados para manter o relatório inequívoco."""
        identifiers = [case.id for case in self.cases]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Os identificadores dos casos devem ser únicos.")
        return self


@dataclass(slots=True)
class EvaluationCounts:
    """Contagens com denominadores explícitos para métricas comparáveis."""

    received: int = 0
    structurally_valid: int = 0
    grounded_excerpt: int = 0
    unique_grounded: int = 0
    labeled_answers: int = 0
    exact_answer_matches: int = 0

    def add(self, other: "EvaluationCounts") -> None:
        """Acumula os resultados de outro caso."""
        self.received += other.received
        self.structurally_valid += other.structurally_valid
        self.grounded_excerpt += other.grounded_excerpt
        self.unique_grounded += other.unique_grounded
        self.labeled_answers += other.labeled_answers
        self.exact_answer_matches += other.exact_answer_matches

    def as_report(self) -> dict[str, object]:
        """Expõe contagens e taxas; sem denominador, a taxa é nula."""
        return {
            "counts": asdict(self),
            "rates": {
                "structure_valid_rate": _ratio(self.structurally_valid, self.received),
                "excerpt_found_rate": _ratio(self.grounded_excerpt, self.structurally_valid),
                "unique_rate": _ratio(self.unique_grounded, self.grounded_excerpt),
                "answer_exact_match_rate": _ratio(self.exact_answer_matches, self.labeled_answers),
            },
        }


@dataclass(slots=True)
class EvaluationIssue:
    """Problema de uma pergunta específica, sem registrar seu texto."""

    question_index: int
    reason: str


@dataclass(slots=True)
class CaseReport:
    """Resultado de um caso, incluindo motivos de descarte."""

    id: str
    counts: EvaluationCounts = field(default_factory=EvaluationCounts)
    issues: list[EvaluationIssue] = field(default_factory=list)

    def as_report(self) -> dict[str, object]:
        """Converte o resultado em um objeto JSON serializável."""
        return {
            "id": self.id,
            **self.counts.as_report(),
            "issues": [asdict(issue) for issue in self.issues],
        }


def _ratio(numerator: int, denominator: int) -> float | None:
    """Não confunde ausência de dados com uma avaliação igual a zero."""
    return numerator / denominator if denominator else None


def _normalize(value: str) -> str:
    """Segue a normalização de referências da geração: NFKC e espaços."""
    return " ".join(unicodedata.normalize("NFKC", value).split()).casefold()


def evaluate_case(case: EvaluationCase) -> CaseReport:
    """Verifica estrutura, citação, diversidade e gabarito textual opcional.

    A pontuação de respostas compara somente perguntas que passariam pelas
    validações estruturais, de referência e deduplicação do produto.
    """
    report = CaseReport(id=case.id)
    source = _normalize(case.source_text)
    seen: set[tuple[QuestionType, str]] = set()

    for index, raw in enumerate(case.questions):
        report.counts.received += 1
        try:
            question = Question.model_validate(raw)
        except ValidationError:
            report.issues.append(EvaluationIssue(index, "invalid_structure"))
            continue

        report.counts.structurally_valid += 1
        if _normalize(question.source_excerpt) not in source:
            report.issues.append(EvaluationIssue(index, "excerpt_not_found"))
            continue

        report.counts.grounded_excerpt += 1
        normalized_statement = " ".join(question.statement.casefold().split())
        key = (question.type, normalized_statement)
        if key in seen:
            report.issues.append(EvaluationIssue(index, "duplicate_statement"))
            continue

        seen.add(key)
        report.counts.unique_grounded += 1
        expected = case.expected_answers[index] if case.expected_answers else None
        if expected is None:
            continue

        report.counts.labeled_answers += 1
        if _normalize(question.answer) == _normalize(expected):
            report.counts.exact_answer_matches += 1
        else:
            report.issues.append(EvaluationIssue(index, "answer_exact_mismatch"))

    return report


def evaluate_dataset(dataset: EvaluationDataset) -> dict[str, object]:
    """Avalia casos offline e agrega os numeradores de cada métrica.

    Não calcula médias de taxas por caso; agrega os contadores para evitar
    distorções entre casos com quantidades diferentes de perguntas.
    """
    totals = EvaluationCounts()
    reports: list[dict[str, object]] = []
    for case in dataset.cases:
        case_report = evaluate_case(case)
        totals.add(case_report.counts)
        reports.append(case_report.as_report())
    return {"version": dataset.version, "cases": reports, "summary": totals.as_report()}
