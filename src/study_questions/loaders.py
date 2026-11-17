"""Carregamento de documentos de estudo nos formatos TXT, MD e PDF."""

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

_TEXT_EXTENSIONS = frozenset({".txt", ".md"})
_PDF_EXTENSION = ".pdf"

# Limites conservadores alinhados ao upload de 10 MB da interface.
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 250
MAX_EXTRACTED_CHARACTERS = 2_000_000


class DocumentError(ValueError):
    """Representa um erro durante a leitura de um documento."""


class UnsupportedFormatError(DocumentError):
    """Indica que o formato do documento não é suportado."""


class EmptyDocumentError(DocumentError):
    """Indica que o documento não possui texto extraível."""


class DocumentLimitError(DocumentError):
    """Indica que o documento excede os limites de processamento."""


def parse_document(data: bytes, filename: str) -> str:
    """Extrai texto de bytes, rejeitando documentos acima dos limites.

    Args:
        data: Conteúdo binário do documento.
        filename: Nome do arquivo utilizado para identificar o formato.

    Returns:
        Texto extraído e sem espaços nas extremidades.

    Raises:
        UnsupportedFormatError: Se a extensão não for suportada.
        DocumentLimitError: Se algum limite de processamento for excedido.
        EmptyDocumentError: Se não houver texto extraível.
        DocumentError: Se o PDF for inválido ou protegido.
    """
    extension = Path(filename).suffix.lower()
    _check_extension(extension)
    _check_size(len(data))

    if extension in _TEXT_EXTENSIONS:
        text = _decode_text(data)
    else:
        text = _extract_pdf_text(BytesIO(data))

    return _validate_text(text)


def load_document(path: Path) -> str:
    """Carrega TXT/MD/PDF do disco evitando cópia integral de PDFs.

    Args:
        path: Caminho para o documento.

    Returns:
        Texto extraído do documento.

    Raises:
        OSError: Se o arquivo não puder ser aberto.
        DocumentError: Se o documento for inválido ou exceder limites.
    """
    extension = path.suffix.lower()
    _check_extension(extension)
    _check_size(path.stat().st_size)

    if extension in _TEXT_EXTENSIONS:
        return parse_document(path.read_bytes(), path.name)

    # PdfReader aceita um objeto de arquivo binário com read/seek.
    # Evita duplicar o PDF inteiro com Path.read_bytes() + BytesIO().
    with path.open("rb") as stream:
        text = _extract_pdf_text(stream)
    return _validate_text(text)


def _check_extension(extension: str) -> None:
    """Valida extensões sem ler bytes desnecessários."""
    if extension not in _TEXT_EXTENSIONS and extension != _PDF_EXTENSION:
        raise UnsupportedFormatError("Formato não suportado. Utilize TXT, MD ou PDF.")


def _check_size(size_bytes: int) -> None:
    """Interrompe o carregamento de arquivos acima do tamanho permitido."""
    if size_bytes > MAX_DOCUMENT_BYTES:
        raise DocumentLimitError(
            f"O arquivo excede o limite de {MAX_DOCUMENT_BYTES // (1024 * 1024)} MB."
        )


def _validate_text(text: str) -> str:
    """Rejeita conteúdo vazio ou texto excessivamente grande."""
    stripped = text.strip()
    if len(stripped) > MAX_EXTRACTED_CHARACTERS:
        raise DocumentLimitError("O texto extraído excede o limite de caracteres.")
    if not stripped:
        raise EmptyDocumentError(
            "O documento não possui texto extraível. "
            "PDFs escaneados sem camada de texto não são suportados."
        )
    return stripped


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


def _extract_pdf_text(stream: BinaryIO) -> str:
    """Extrai páginas de um PDF com limites de páginas e caracteres.

    Args:
        stream: Arquivo PDF aberto em modo binário, com read/seek.

    Returns:
        Texto concatenado, preservando a ordem e separadores das páginas.

    Raises:
        DocumentLimitError: Se o PDF exceder limites predefinidos.
        DocumentError: Se o PDF estiver corrompido ou protegido por senha.
    """
    try:
        reader = PdfReader(stream)

        if reader.is_encrypted:
            raise DocumentError("PDF protegido por senha não é suportado.")

        if len(reader.pages) > MAX_PDF_PAGES:
            raise DocumentLimitError(f"PDF excede o limite de {MAX_PDF_PAGES} páginas.")

        parts: list[str] = []
        total_characters = 0
        for page in reader.pages:
            page_text = page.extract_text() or ""
            total_characters += len(page_text) + (2 if parts else 0)
            if total_characters > MAX_EXTRACTED_CHARACTERS:
                raise DocumentLimitError("O texto extraído excede o limite de caracteres.")
            parts.append(page_text)

        return "\n\n".join(parts)

    except PdfReadError as exc:
        raise DocumentError("Não foi possível ler o PDF. O arquivo pode estar corrompido.") from exc
