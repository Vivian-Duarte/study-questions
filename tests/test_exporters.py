"""Testes dos exportadores JSON e Anki."""

import csv
import json
from io import StringIO
from pathlib import Path

from study_questions.exporters import (
    export_anki_tsv,
    export_json,
    save_anki_tsv,
    save_json,
)
from study_questions.models import Question, QuestionSet, QuestionType


def _question_set() -> QuestionSet:
    """Cria um conjunto com perguntas abertas e objetivas."""
    return QuestionSet(
        questions=[
            Question(
                type=QuestionType.OPEN,
                statement="O que é Python?",
                answer="Uma linguagem de programação.",
                explanation="Python é uma linguagem de alto nível.",
                source_excerpt="Python é uma linguagem de programação.",
            ),
            Question(
                type=QuestionType.MULTIPLE_CHOICE,
                statement="Qual linguagem aparece no texto?",
                answer="Python",
                explanation="O texto menciona Python.",
                source_excerpt="Python é uma linguagem de programação.",
                options=["Python", "Java", "C++"],
            ),
        ]
    )


def _anki_rows(question_set: QuestionSet) -> list[list[str]]:
    """Lê as linhas de dados do texto exportado para Anki."""
    output = export_anki_tsv(question_set)
    rows = output.splitlines(keepends=True)

    return list(
        csv.reader(
            StringIO("".join(rows[4:])),
            delimiter="\t",
        )
    )


def test_json_roundtrip_preserves_all_fields() -> None:
    """Preserva todo o conjunto após exportar e importar JSON."""
    original = _question_set()

    restored = QuestionSet.model_validate_json(export_json(original))

    assert restored == original


def test_json_has_indentation_and_unicode() -> None:
    """Exporta JSON formatado mantendo os acentos."""
    output = export_json(_question_set())

    assert output.startswith('{\n  "questions": [')
    assert "programação" in output
    assert output.endswith("\n")


def test_anki_has_import_headers() -> None:
    """Inclui cabeçalhos de tabulação, HTML e etiquetas."""
    output = export_anki_tsv(_question_set())

    assert output.startswith(
        "#separator:Tab\n#html:true\n#columns:Front\tBack\tTags\n#tags column:3\n"
    )


def test_anki_creates_one_row_per_question() -> None:
    """Mantém três campos por pergunta exportada."""
    rows = _anki_rows(_question_set())

    assert len(rows) == 2
    assert all(len(row) == 3 for row in rows)


def test_open_question_contains_front_and_answer() -> None:
    """Exporta o enunciado aberto e a resposta no verso."""
    front, back, _ = _anki_rows(_question_set())[0]

    assert front == "O que é Python?"
    assert "<ol" not in front
    assert "<b>Resposta:</b> Uma linguagem de programação." in back


def test_multiple_choice_preserves_options() -> None:
    """Preserva as alternativas de múltipla escolha na frente."""
    front, back, _ = _anki_rows(_question_set())[1]

    assert '<ol type="A">' in front
    assert "<li>Python</li><li>Java</li><li>C++</li>" in front
    assert "<b>Resposta:</b> Python" in back


def test_anki_preserves_explanation_and_source() -> None:
    """Exibe explicação e referência no verso."""
    back = _anki_rows(_question_set())[0][1]

    assert "<b>Explicação:</b> Python é uma linguagem de alto nível." in back
    assert "<b>Fonte:</b> Python é uma linguagem de programação." in back


def test_anki_tags_distinguish_question_types() -> None:
    """Insere etiquetas para separar questões abertas e objetivas."""
    rows = _anki_rows(_question_set())

    assert rows[0][2] == "study_questions open"
    assert rows[1][2] == "study_questions multiple_choice"


def test_anki_escapes_html_from_content() -> None:
    """Escapa HTML proveniente do conteúdo do documento."""
    example = QuestionSet(
        questions=[
            Question(
                type=QuestionType.MULTIPLE_CHOICE,
                statement="Qual é o valor de <script>alert(1)</script>?",
                answer="A&B",
                explanation="Use <b> sem interpretar HTML.",
                source_excerpt="O texto traz a expressão A&B.",
                options=["A&B", "<img src=x>", "C"],
            )
        ]
    )

    front, back, _ = _anki_rows(example)[0]

    assert "<script>" not in front
    assert "&lt;script&gt;" in front
    assert "&lt;img src=x&gt;" in front
    assert "A&amp;B" in front
    assert "A&amp;B" in back
    assert "&lt;b&gt;" in back


def test_anki_multiline_text_stays_in_single_row() -> None:
    """Converte quebras de linha sem criar novas linhas TSV."""
    example = QuestionSet(
        questions=[
            Question(
                type=QuestionType.OPEN,
                statement="Primeira linha\nsegunda linha?",
                answer="Resposta\tseparada\npor linhas",
                source_excerpt="Trecho\noriginal",
            )
        ]
    )

    output = export_anki_tsv(example)

    assert len(output.splitlines()) == 5

    row = _anki_rows(example)[0]

    assert "Primeira linha<br>segunda linha?" in row[0]
    assert "Resposta&#9;separada<br>por linhas" in row[1]
    assert "Trecho<br>original" in row[1]


def test_anki_omits_empty_explanation() -> None:
    """Não inclui seção vazia quando não há explicação."""
    example = QuestionSet(
        questions=[
            Question(
                type=QuestionType.OPEN,
                statement="Quem escreveu o código?",
                answer="Uma pessoa.",
                source_excerpt="Uma pessoa escreveu o código.",
            )
        ]
    )

    back = _anki_rows(example)[0][1]

    assert "Explicação" not in back
    assert "Fonte:" in back


def test_export_does_not_change_questions() -> None:
    """Mantém os objetos Pydantic originais após exportar."""
    original = _question_set()
    before = original.model_dump_json()

    export_json(original)
    export_anki_tsv(original)

    assert original.model_dump_json() == before


def test_json_export_is_deterministic() -> None:
    """Produz a mesma saída para o mesmo conjunto de perguntas."""
    original = _question_set()

    assert export_json(original) == export_json(original)


def test_anki_export_is_deterministic() -> None:
    """Produz a mesma saída Anki para o mesmo conjunto."""
    original = _question_set()

    assert export_anki_tsv(original) == export_anki_tsv(original)


def test_saves_json_in_utf8(tmp_path: Path) -> None:
    """Grava um arquivo JSON que pode ser lido posteriormente."""
    destination = tmp_path / "questoes.json"

    save_json(_question_set(), destination)

    content = destination.read_text(encoding="utf-8")

    assert json.loads(content)["questions"][0]["type"] == "open"
    assert "programação" in content


def test_saves_anki_text_in_utf8(tmp_path: Path) -> None:
    """Grava o texto importável no Anki."""
    destination = tmp_path / "questoes_anki.txt"

    save_anki_tsv(_question_set(), destination)

    content = destination.read_text(encoding="utf-8")

    assert content.startswith("#separator:Tab")
    assert "programação" in content
    assert content == export_anki_tsv(_question_set())
