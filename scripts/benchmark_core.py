"""Benchmark local dos módulos do Study Questions, sem chamadas à API.

Exemplos:
    python scripts/benchmark_core.py --words 10000 --repeat 5
    python scripts/benchmark_core.py --words 50000 --repeat 3 --json

Os tempos são medições locais ilustrativas, não metas obrigatórias em CI.
O pico é de alocações Python rastreadas por tracemalloc, não de RAM total do processo.
"""

import argparse
import gc
import json
import statistics
import tracemalloc
from collections.abc import Callable
from io import BytesIO
from time import perf_counter
from typing import Any

from reportlab.pdfgen import canvas

from study_questions.chunking import split_text
from study_questions.exporters import export_anki_tsv, export_json
from study_questions.loaders import parse_document
from study_questions.models import Question, QuestionSet, QuestionType
from study_questions.quiz import score_answers


def _example_questions(count: int) -> QuestionSet:
    """Cria perguntas válidas para medições reproduzíveis."""
    return QuestionSet(
        questions=[
            Question(
                type=QuestionType.MULTIPLE_CHOICE,
                statement=f"Qual linguagem aparece na questão número {index + 1}?",
                answer="Python",
                explanation="A fonte menciona Python.",
                source_excerpt="Python é uma linguagem de programação.",
                options=["Java", "Python", "Ruby"],
            )
            for index in range(count)
        ]
    )


def _example_pdf(pages: int) -> bytes:
    """Gera um PDF sintético em memória, sem gravar dados pessoais."""
    output = BytesIO()
    pdf = canvas.Canvas(output)
    for index in range(pages):
        pdf.drawString(
            72,
            720,
            f"Pagina {index + 1}: Python e uma linguagem de programacao.",
        )
        pdf.showPage()
    pdf.save()
    return output.getvalue()


def _measure(action: Callable[[], object], repeat: int) -> dict[str, float | int]:
    """Mede tempo mediano e pico aproximado de alocações Python."""
    action()  # Aquecimento: evita incluir o custo do primeiro uso das bibliotecas.
    durations: list[float] = []
    for _ in range(repeat):
        gc.collect()
        started = perf_counter()
        action()
        durations.append((perf_counter() - started) * 1000)

    gc.collect()
    tracemalloc.start()
    try:
        action()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    return {
        "median_ms": round(statistics.median(durations), 3),
        "peak_python_kib": round(peak / 1024, 1),
        "runs": repeat,
    }


def run_benchmarks(
    *, words: int = 10000, questions: int = 100, pdf_pages: int = 3, repeat: int = 5
) -> dict[str, Any]:
    """Executa os cenários determinísticos, sem dependência do Gemini.

    Args:
        words: Quantidade de palavras no texto sintético.
        questions: Quantidade de perguntas nos exportadores e na pontuação.
        pdf_pages: Quantidade de páginas sintéticas a extrair; zero para ignorar PDF.
        repeat: Número de repetições por cenário.

    Returns:
        Resultados com tempos, memória rastreada e parâmetros utilizados.

    Raises:
        ValueError: Se algum parâmetro estiver fora dos limites do benchmark.
    """
    if not 1 <= words <= 250_000:
        raise ValueError("words deve estar entre 1 e 250000.")
    if not 1 <= questions <= 500:
        raise ValueError("questions deve estar entre 1 e 500.")
    if not 0 <= pdf_pages <= 20:
        raise ValueError("pdf_pages deve estar entre 0 e 20.")
    if not 1 <= repeat <= 20:
        raise ValueError("repeat deve estar entre 1 e 20.")

    text = ("Python " * words).strip()
    question_set = _example_questions(questions)
    answers = {index: "Python" if index % 2 == 0 else "Java" for index in range(questions)}

    cases: dict[str, Callable[[], object]] = {
        "chunking": lambda: split_text(text, max_words=1000, overlap_words=100),
        "json_export": lambda: export_json(question_set),
        "anki_export": lambda: export_anki_tsv(question_set),
        "quiz_score": lambda: score_answers(question_set.questions, answers),
    }
    if pdf_pages:
        pdf_data = _example_pdf(pdf_pages)
        cases["pdf_extraction"] = lambda: parse_document(pdf_data, "benchmark.pdf")

    return {
        "parameters": {
            "words": words,
            "questions": questions,
            "pdf_pages": pdf_pages,
            "repeat": repeat,
        },
        "results": {name: _measure(action, repeat) for name, action in cases.items()},
    }


def main() -> None:
    """Executa o benchmark por linha de comando."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--words", type=int, default=10000)
    parser.add_argument("--questions", type=int, default=100)
    parser.add_argument("--pdf-pages", type=int, default=3)
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--json", action="store_true", help="Imprime resultado em JSON")
    args = parser.parse_args()
    try:
        report = run_benchmarks(
            words=args.words,
            questions=args.questions,
            pdf_pages=args.pdf_pages,
            repeat=args.repeat,
        )
    except ValueError as exc:
        parser.error(str(exc))

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("Study Questions — benchmark local (sem Gemini)")
        for name, values in report["results"].items():
            print(
                f"{name:16} {values['median_ms']:>9.3f} ms (mediana) "
                f"| {values['peak_python_kib']:>9.1f} KiB pico Python"
            )
        print("Medição isolada: compare execuções no mesmo computador e ambiente.")


if __name__ == "__main__":
    main()
