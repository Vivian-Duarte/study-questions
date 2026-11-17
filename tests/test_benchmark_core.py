"""Testes de execução dos benchmarks sintéticos, sem chamadas ao Gemini."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "benchmark_core.py"


def test_benchmark_outputs_valid_json() -> None:
    """Confirma que o script roda sem rede e produz métricas não negativas."""
    completed = subprocess.run(  # noqa: S603 (S não habilitado no projeto)
        [
            sys.executable,
            str(SCRIPT),
            "--words",
            "100",
            "--questions",
            "2",
            "--pdf-pages",
            "0",
            "--repeat",
            "1",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    output = json.loads(completed.stdout)
    assert output["parameters"]["words"] == 100
    assert set(output["results"]) == {
        "chunking",
        "json_export",
        "anki_export",
        "quiz_score",
    }
    for measurements in output["results"].values():
        assert measurements["median_ms"] >= 0
        assert measurements["peak_python_kib"] >= 0
        assert measurements["runs"] == 1


@pytest.mark.parametrize(
    "arguments",
    [
        ["--words", "0"],
        ["--repeat", "0"],
        ["--pdf-pages", "21"],
    ],
)
def test_benchmark_rejects_invalid_parameters(arguments: list[str]) -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert completed.returncode != 0
    assert "error" in completed.stderr.lower()
