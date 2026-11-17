"""Testes offline das métricas e da validação do dataset de avaliação."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from study_questions.evaluation import (
    EvaluationCase,
    EvaluationDataset,
    evaluate_case,
    evaluate_dataset,
)

SAMPLE = Path(__file__).resolve().parents[1] / "datasets" / "evaluation" / "sample.json"


def test_sample_dataset_aggregate_metrics() -> None:
    dataset = EvaluationDataset.model_validate_json(SAMPLE.read_text(encoding="utf-8"))
    result = evaluate_dataset(dataset)
    summary = result["summary"]
    assert summary["counts"] == {
        "received": 6,
        "structurally_valid": 5,
        "grounded_excerpt": 4,
        "unique_grounded": 3,
        "labeled_answers": 3,
        "exact_answer_matches": 2,
    }
    assert summary["rates"] == {
        "structure_valid_rate": 5 / 6,
        "excerpt_found_rate": 4 / 5,
        "unique_rate": 3 / 4,
        "answer_exact_match_rate": 2 / 3,
    }
    assert result["version"] == 1
    assert [entry["id"] for entry in result["cases"]] == [
        "python_conceitos_basicos",
        "exemplos_de_falhas_controladas",
    ]


def test_issues_include_no_sensitive_question_content() -> None:
    dataset = EvaluationDataset.model_validate_json(SAMPLE.read_text(encoding="utf-8"))
    result = evaluate_dataset(dataset)
    reasons = [item["reason"] for item in result["cases"][1]["issues"]]
    assert reasons == [
        "answer_exact_mismatch",
        "duplicate_statement",
        "excerpt_not_found",
        "invalid_structure",
    ]
    assert "O ferro funde" not in json.dumps(result, ensure_ascii=False)


def test_empty_case_rates_are_unknown_not_zero() -> None:
    case = EvaluationCase(id="sem_perguntas", source_text="Texto.")
    report = evaluate_case(case).as_report()
    assert report["counts"]["received"] == 0
    assert all(rate is None for rate in report["rates"].values())


def test_unlabeled_question_does_not_count_as_wrong() -> None:
    data = EvaluationDataset.model_validate_json(SAMPLE.read_text(encoding="utf-8"))
    case = data.cases[0].model_copy(update={"expected_answers": []})
    report = evaluate_case(case).as_report()
    assert report["counts"]["labeled_answers"] == 0
    assert report["rates"]["answer_exact_match_rate"] is None


def test_text_normalization_case_and_nfkc() -> None:
    case = EvaluationCase(
        id="normalizacao",
        source_text="Python utiliza Unicode NFKC.",
        questions=[
            {
                "type": "open",
                "statement": "Qual normalização aparece neste texto?",
                "answer": " NFKC  ",
                "source_excerpt": " Python utiliza  Unicode NFKC. ",
                "explanation": "",
                "options": [],
            }
        ],
        expected_answers=["nfkc"],
    )
    report = evaluate_case(case)
    assert report.counts.grounded_excerpt == 1
    assert report.counts.exact_answer_matches == 1


def test_duplicate_is_by_type_and_normalized_statement() -> None:
    dataset = EvaluationDataset.model_validate_json(SAMPLE.read_text(encoding="utf-8"))
    raw = dataset.cases[0].questions[0]
    assert isinstance(raw, dict)
    alternate = dict(raw, statement="  QUAL FUNÇÃO retorna o tamanho de uma sequência? ")
    case = dataset.cases[0].model_copy(update={"questions": [raw, alternate]})
    assert evaluate_case(case).counts.unique_grounded == 1


def test_distinct_types_are_not_duplicates() -> None:
    dataset = EvaluationDataset.model_validate_json(SAMPLE.read_text(encoding="utf-8"))
    raw = dataset.cases[0].questions[0]
    assert isinstance(raw, dict)
    open_version = dict(raw, type="open", options=[])
    case = dataset.cases[0].model_copy(update={"questions": [raw, open_version]})
    assert evaluate_case(case).counts.unique_grounded == 2


def test_reference_annotations_must_match_question_count() -> None:
    with pytest.raises(ValidationError, match="mesmo tamanho"):
        EvaluationCase(
            id="x",
            source_text="Material.",
            questions=[{"type": "open"}],
            expected_answers=["sim", "não"],
        )


def test_blank_reference_answer_rejected() -> None:
    with pytest.raises(ValidationError, match="não podem ser vazias"):
        EvaluationCase(id="x", source_text="Material.", questions=[{}], expected_answers=[" "])


def test_dataset_must_have_unique_ids() -> None:
    with pytest.raises(ValidationError, match="únicos"):
        EvaluationDataset(
            version=1,
            cases=[
                EvaluationCase(id="mesmo", source_text="Texto."),
                EvaluationCase(id="mesmo", source_text="Texto."),
            ],
        )


def test_dataset_rejects_unsupported_version() -> None:
    with pytest.raises(ValidationError):
        EvaluationDataset(version=2, cases=[EvaluationCase(id="x", source_text="Texto.")])


def test_invalid_structure_rejected_before_other_metrics() -> None:
    case = EvaluationCase(
        id="erro",
        source_text="Material.",
        questions=[{"type": "multiple_choice", "statement": "Onde está a resposta?"}],
    )
    report = evaluate_case(case).as_report()
    assert report["counts"]["structurally_valid"] == 0
    assert report["issues"][0]["reason"] == "invalid_structure"


def test_invalid_question_item_other_than_object_is_handled() -> None:
    case = EvaluationCase(id="erro", source_text="Material.", questions=[None, "texto", 1])
    report = evaluate_case(case).as_report()
    assert report["counts"]["received"] == 3
    assert len(report["issues"]) == 3


def test_no_question_contents_in_aggregate_report() -> None:
    data = EvaluationDataset.model_validate_json(SAMPLE.read_text(encoding="utf-8"))
    report = evaluate_dataset(data)
    assert "source_text" not in json.dumps(report)
    assert "questions" not in report
