"""Valida o CLI de avaliação offline sem chave Gemini."""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "evaluate_questions.py"
SAMPLE = Path(__file__).resolve().parents[1] / "datasets" / "evaluation" / "sample.json"


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )


def test_script_outputs_readable_summary() -> None:
    result = _run("--dataset", str(SAMPLE))
    assert result.returncode == 0, result.stderr
    assert "Recebidas: 6" in result.stdout
    assert "Gabaritos de referência" in result.stdout
    assert "semântica" in result.stdout


def test_script_outputs_machine_readable_json() -> None:
    result = _run("--dataset", str(SAMPLE), "--json")
    assert result.returncode == 0, result.stderr
    parsed = json.loads(result.stdout)
    assert parsed["summary"]["counts"]["unique_grounded"] == 3


def test_script_rejects_missing_dataset() -> None:
    result = _run("--dataset", "nao-existe-essa-amostra.json")
    assert result.returncode != 0
    assert "Conjunto de avaliação inválido" in result.stderr


def test_script_rejects_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{bad", encoding="utf-8")
    result = _run("--dataset", str(path))
    assert result.returncode != 0
    assert "Conjunto de avaliação inválido" in result.stderr
