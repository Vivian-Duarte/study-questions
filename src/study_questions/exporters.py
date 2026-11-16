"""Exportação de conjuntos de perguntas para JSON e Anki."""

import csv
from html import escape
from io import StringIO
from pathlib import Path

from study_questions.models import Question, QuestionSet, QuestionType

ANKI_HEADERS = "#separator:Tab\n#html:true\n#columns:Front\tBack\tTags\n#tags column:3\n"


def export_json(question_set: QuestionSet) -> str:
    """Converte perguntas validadas em JSON legível.

    Args:
        question_set: Conjunto de perguntas validado.

    Returns:
        Conteúdo JSON formatado em UTF-8 quando salvo.
    """
    return question_set.model_dump_json(indent=2) + "\n"


def export_anki_tsv(question_set: QuestionSet) -> str:
    """Converte perguntas em texto tabulado compatível com Anki.

    Args:
        question_set: Conjunto de perguntas validado.

    Returns:
        Conteúdo com frente, verso e etiquetas por pergunta.
    """
    output = StringIO(newline="")
    output.write(ANKI_HEADERS)
    writer = csv.writer(output, delimiter="\t", lineterminator="\n")

    for question in question_set.questions:
        writer.writerow(
            (
                _anki_front(question),
                _anki_back(question),
                f"study_questions {question.type.value}",
            )
        )

    return output.getvalue()


def save_json(question_set: QuestionSet, path: Path) -> None:
    """Salva perguntas em um arquivo JSON UTF-8.

    Args:
        question_set: Perguntas a exportar.
        path: Caminho de destino do arquivo.
    """
    path.write_text(
        export_json(question_set),
        encoding="utf-8",
        newline="\n",
    )


def save_anki_tsv(question_set: QuestionSet, path: Path) -> None:
    """Salva flashcards em texto UTF-8 importável pelo Anki.

    Args:
        question_set: Perguntas a exportar.
        path: Caminho de destino, preferencialmente com extensão .txt.
    """
    path.write_text(
        export_anki_tsv(question_set),
        encoding="utf-8",
        newline="\n",
    )


def _as_html(value: str) -> str:
    """Escapa conteúdo e converte quebras de linha em HTML."""
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    return escape(normalized, quote=True).replace("\n", "<br>").replace("\t", "&#9;")


def _anki_front(question: Question) -> str:
    """Monta a frente com o enunciado e eventuais alternativas."""
    statement = _as_html(question.statement)

    if question.type == QuestionType.MULTIPLE_CHOICE:
        options = "".join(f"<li>{_as_html(option)}</li>" for option in question.options)
        return f'{statement}<br><ol type="A">{options}</ol>'

    return statement


def _anki_back(question: Question) -> str:
    """Monta o verso com resposta, explicação e fonte."""
    parts = [f"<b>Resposta:</b> {_as_html(question.answer)}"]

    if question.explanation:
        parts.append(f"<b>Explicação:</b> {_as_html(question.explanation)}")

    parts.append(f"<b>Fonte:</b> {_as_html(question.source_excerpt)}")

    return "<br><br>".join(parts)
