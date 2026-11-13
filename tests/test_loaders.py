"""Testes dos carregadores de documentos."""

from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfWriter
from reportlab.pdfgen import canvas

from study_questions.loaders import (
    DocumentError,
    EmptyDocumentError,
    UnsupportedFormatError,
    load_document,
    parse_document,
)


def _make_pdf(lines: list[str]) -> bytes:
    """Cria um PDF de teste com uma linha por página.

    Args:
        lines: Textos a inserir nas páginas.

    Returns:
        Conteúdo binário do PDF.
    """
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)

    for line in lines:
        pdf.drawString(72, 720, line)
        pdf.showPage()

    pdf.save()
    return buffer.getvalue()


def _blank_pdf() -> bytes:
    """Cria um PDF válido com uma página sem texto."""
    buffer = BytesIO()
    writer = PdfWriter()

    writer.add_blank_page(width=300, height=300)
    writer.write(buffer)

    return buffer.getvalue()


def _encrypted_pdf() -> bytes:
    """Cria um PDF protegido por senha."""
    buffer = BytesIO()
    writer = PdfWriter()

    writer.add_blank_page(width=300, height=300)
    writer.encrypt("test-password")
    writer.write(buffer)

    return buffer.getvalue()


def test_reads_utf8_text() -> None:
    """Extrai texto de um arquivo TXT codificado em UTF-8."""
    content = "Olá, mundo! Programação.".encode()
    result = parse_document(content, "aula.txt")

    assert result == "Olá, mundo! Programação."


def test_reads_markdown_with_bom() -> None:
    """Aceita Markdown UTF-8 com BOM e extensão maiúscula."""
    content = "# Introdução ao Python".encode("utf-8-sig")

    result = parse_document(content, "aula.MD")

    assert result == "# Introdução ao Python"


def test_reads_cp1252_text() -> None:
    """Utiliza CP1252 quando o conteúdo não for UTF-8."""
    content = "Introdução à computação".encode("cp1252")

    result = parse_document(content, "aula.txt")

    assert result == "Introdução à computação"


def test_extracts_text_from_pdf() -> None:
    """Extrai texto de um PDF válido."""
    content = _make_pdf(["Hello study world"])

    result = parse_document(content, "aula.pdf")

    assert "Hello study world" in result


def test_extracts_multiple_pdf_pages() -> None:
    """Preserva o texto de todas as páginas do PDF."""
    content = _make_pdf(["First page", "Second page"])

    result = parse_document(content, "aula.pdf")

    assert "First page" in result
    assert "Second page" in result
    assert result.index("First page") < result.index("Second page")


@pytest.mark.parametrize(
    "filename,content",
    [
        ("aula.txt", b"   "),
        ("aula.md", b"\n\n"),
    ],
)
def test_rejects_empty_text(
    filename: str,
    content: bytes,
) -> None:
    """Rejeita arquivos de texto sem conteúdo útil."""
    with pytest.raises(EmptyDocumentError):
        parse_document(content, filename)


def test_rejects_blank_pdf() -> None:
    """Rejeita PDFs que não possuem texto extraível."""
    with pytest.raises(EmptyDocumentError):
        parse_document(_blank_pdf(), "aula.pdf")


def test_rejects_corrupted_pdf() -> None:
    """Rejeita arquivos que não são PDFs válidos."""
    with pytest.raises(DocumentError):
        parse_document(b"invalid pdf content", "aula.pdf")


def test_rejects_encrypted_pdf() -> None:
    """Rejeita PDFs protegidos por senha."""
    with pytest.raises(DocumentError, match="senha"):
        parse_document(_encrypted_pdf(), "aula.pdf")


def test_rejects_unsupported_extension() -> None:
    """Rejeita formatos não suportados."""
    with pytest.raises(UnsupportedFormatError):
        parse_document(b"document content", "aula.docx")


def test_loads_document_from_disk(tmp_path: Path) -> None:
    """Carrega um arquivo armazenado no disco."""
    path = tmp_path / "aula.md"
    path.write_text("# Aula de Python", encoding="utf-8")

    result = load_document(path)

    assert result == "# Aula de Python"
