"""Read supported resumes without OCR or arbitrary format guessing."""

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from app.core.exceptions import ResumeReadError

SUPPORTED_SUFFIXES = {".pdf", ".md", ".txt"}
MAX_RESUME_BYTES = 5 * 1024 * 1024


@dataclass(frozen=True)
class ResumeDocument:
    source_id: str
    text: str
    lines: tuple[tuple[str, str], ...]

    @property
    def prompt_text(self) -> str:
        return "\n".join(f"[{locator}] {line}" for locator, line in self.lines)

    def locate_quote(self, quote: str) -> str | None:
        needle = normalize_text(quote)
        for locator, line in self.lines:
            if needle and needle in normalize_text(line):
                return locator
        return None


def load_resume(path: str | Path) -> ResumeDocument:
    file_path = Path(path)
    if not file_path.is_file():
        raise ResumeReadError("Resume file does not exist or is not a regular file.")
    suffix = file_path.suffix.casefold()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ResumeReadError("Unsupported resume format. Use PDF, Markdown, or TXT.")
    try:
        size = file_path.stat().st_size
    except OSError:
        raise ResumeReadError("Resume file metadata could not be read.") from None
    if size == 0:
        raise ResumeReadError("Resume file is empty.")
    if size > MAX_RESUME_BYTES:
        raise ResumeReadError("Resume file exceeds the 5 MB limit.")
    return _load_pdf(file_path) if suffix == ".pdf" else _load_text(file_path)


def _load_text(path: Path) -> ResumeDocument:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raise ResumeReadError("Resume text must use UTF-8 encoding.") from None
    except OSError:
        raise ResumeReadError("Resume text could not be read.") from None
    return _build_document(path, (("line", text),))


def _load_pdf(path: Path) -> ResumeDocument:
    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            raise ResumeReadError("Encrypted PDF resumes are not supported.")
        pages = [
            (f"page:{page_number}", page.extract_text() or "")
            for page_number, page in enumerate(reader.pages, start=1)
        ]
    except ResumeReadError:
        raise
    except Exception:
        raise ResumeReadError("PDF resume could not be parsed.") from None
    return _build_document(path, pages)


def _build_document(
    path: Path,
    sections: list[tuple[str, str]] | tuple[tuple[str, str], ...],
) -> ResumeDocument:
    located_lines: list[tuple[str, str]] = []
    for section, text in sections:
        for line_number, line in enumerate(text.splitlines(), start=1):
            cleaned = line.strip()
            if cleaned:
                prefix = f"{section}:" if section == "line" else f"{section} line:"
                located_lines.append((f"{prefix}{line_number}", cleaned))
    if not located_lines:
        message = (
            "PDF contains no extractable text; provide a text-layer PDF, Markdown, or TXT."
            if path.suffix.casefold() == ".pdf"
            else "Resume file contains no non-whitespace text."
        )
        raise ResumeReadError(message)
    text = "\n".join(line for _, line in located_lines)
    return ResumeDocument(
        source_id=f"resume:{path.name}",
        text=text,
        lines=tuple(located_lines),
    )


def normalize_text(value: str) -> str:
    return " ".join(value.casefold().split())
