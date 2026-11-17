"""Executa avaliação offline de conjuntos de perguntas anotados.

Exemplo:
    python scripts/evaluate_questions.py --dataset datasets/evaluation/sample.json
    python scripts/evaluate_questions.py --dataset datasets/evaluation/sample.json --json
"""

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from study_questions.evaluation import EvaluationDataset, evaluate_dataset

DEFAULT_DATASET = Path("datasets/evaluation/sample.json")


def main() -> int:
    """Valida o conjunto fornecido e apresenta métricas sem chamar Gemini."""
    parser = argparse.ArgumentParser(description="Avaliação offline do Study Questions")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--json", action="store_true", help="Emite relatório completo em JSON")
    args = parser.parse_args()

    try:
        dataset = EvaluationDataset.model_validate_json(args.dataset.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        parser.error(f"Conjunto de avaliação inválido: {error}")

    report = evaluate_dataset(dataset)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    summary = report["summary"]
    counts = summary["counts"]
    rates = summary["rates"]
    assert isinstance(counts, dict)
    assert isinstance(rates, dict)
    print(f"Study Questions — avaliação offline ({len(dataset.cases)} caso(s))")
    print(f"Recebidas: {counts['received']} | Válidas: {counts['structurally_valid']}")
    print(f"Citações localizadas: {counts['grounded_excerpt']}")
    print(f"Únicas com citação: {counts['unique_grounded']}")
    print(
        "Gabaritos de referência (correspondência textual): "
        f"{counts['exact_answer_matches']}/{counts['labeled_answers']}"
    )
    for name, rate in rates.items():
        display = "N/A" if rate is None else f"{rate:.1%}"
        print(f"{name}: {display}")
    print("Aviso: métricas lexicais não verificam correção factual ou semântica.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
