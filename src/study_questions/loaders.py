"""Carregamento de documentos de estudo nos formatos TXT, MD e PDF."""

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

_TEXT_EXTENSIONS = frozenset({".txt", ".md"})
_PDF_EXTENSION = ".pdf"


class DocumentError(ValueError):
    """Representa um erro durante a leitura de um documento."""


class UnsupportedFormatError(DocumentError):
    """Indica que o formato do documento não é suportado."""


class EmptyDocumentError(DocumentError):
    """Indica que o documento não possui texto extraível."""


def parse_document(data: bytes, filename: str) -> str:
    """Extrai o conteúdo textual de um documento em memória.

    Args:
        data: Conteúdo binário do documento.
        filename: Nome do arquivo utilizado para identificar seu formato.

    Returns:
        Texto extraído e sem espaços nas extremidades.

    Raises:
        UnsupportedFormatError: Se o formato não for suportado.
        EmptyDocumentError: Se não houver texto extraível.
        DocumentError: Se o documento PDF estiver inválido ou protegido.
    """
    extension = Path(filename).suffix.lower()

    if extension in _TEXT_EXTENSIONS:
        text = _decode_text(data)

    elif extension == _PDF_EXTENSION:
        text = _extract_pdf_text(data)

    else:
        raise UnsupportedFormatError("Formato não suportado. Utilize TXT, MD ou PDF.")

    text = text.strip()

    if not text:
        raise EmptyDocumentError(
            "O documento não possui texto extraível. "
            "PDFs escaneados sem camada de texto não são suportados."
        )

    return text


def load_document(path: Path) -> str:
    """Carrega um documento armazenado no sistema de arquivos.

    Args:
        path: Caminho do documento.

    Returns:
        Conteúdo textual do documento.

    Raises:
        OSError: Se o arquivo não puder ser lido.
        DocumentError: Se o documento for inválido ou não suportado.
    """
    return parse_document(
        data=path.read_bytes(),
        filename=path.name,
    )


def _decode_text(data: bytes) -> str:
    """Decodifica documentos de texto.

    Args:
        data: Conteúdo binário do documento.

    Returns:
        Texto decodificado em UTF-8 ou, como alternativa, CP1252.
    """
    try:
        return data.decode("utf-8-sig")

    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def _extract_pdf_text(data: bytes) -> str:
    """Extrai o texto das páginas de um PDF.

    Args:
        data: Conteúdo binário do arquivo PDF.

    Returns:
        Texto extraído de todas as páginas.

    Raises:
        DocumentError: Se o PDF estiver inválido ou protegido por senha.
    """
    try:
        reader = PdfReader(BytesIO(data))

        if reader.is_encrypted:
            raise DocumentError("PDF protegido por senha não é suportado.")

        pages = (page.extract_text() or "" for page in reader.pages)

        return "\n\n".join(pages)

    except PdfReadError as exc:
        raise DocumentError("Não foi possível ler o PDF. O arquivo pode estar corrompido.") from exc
