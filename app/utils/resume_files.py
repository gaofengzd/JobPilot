"""Read supported resumes without OCR or arbitrary format guessing."""

import re
import unicodedata
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from app.core.exceptions import ResumeReadError

SUPPORTED_SUFFIXES = {".pdf", ".md", ".txt"}
MAX_RESUME_BYTES = 5 * 1024 * 1024
MAX_GROUNDING_LINES = 3


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
        if not needle:
            return None
        for locator, line in self.lines:
            if needle in normalize_text(line):
                return locator
        for start in range(len(self.lines)):
            for end in range(start + 1, min(start + MAX_GROUNDING_LINES, len(self.lines))):
                if not _locators_are_consecutive(self.lines[end - 1][0], self.lines[end][0]):
                    break
                span = " ".join(line for _, line in self.lines[start : end + 1])
                if needle in normalize_text(span):
                    return f"{self.lines[start][0]}-{self.lines[end][0]}"
        return None

    def contains_exact_span(self, value: str) -> bool:
        """Accept exact text on one line or across up to three adjacent source lines."""
        needle = normalize_text(value)
        if not needle:
            return False
        for start in range(len(self.lines)):
            for end in range(start, min(start + MAX_GROUNDING_LINES, len(self.lines))):
                if end > start and not _locators_are_consecutive(
                    self.lines[end - 1][0], self.lines[end][0]
                ):
                    break
                span = " ".join(line for _, line in self.lines[start : end + 1])
                if needle in normalize_text(span):
                    return True
        return False


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


def load_resume_bytes(filename: str, data: bytes) -> ResumeDocument:
    """Parse an authorized upload entirely in memory; never accept a server path."""
    safe_name = Path(filename or "").name
    if not safe_name or safe_name in {".", ".."}:
        raise ResumeReadError("Resume upload must include a filename.")
    suffix = Path(safe_name).suffix.casefold()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ResumeReadError("Unsupported resume format. Use PDF, Markdown, or TXT.")
    if not data:
        raise ResumeReadError("Resume file is empty.")
    if len(data) > MAX_RESUME_BYTES:
        raise ResumeReadError("Resume file exceeds the 5 MB limit.")
    path = Path(safe_name)
    if suffix == ".pdf":
        return _load_pdf_stream(path, BytesIO(data))
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ResumeReadError("Resume text must use UTF-8 encoding.") from None
    return _build_document(path, (("line", text),))


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
        return _load_pdf_stream(path, path)
    except ResumeReadError:
        raise
    except Exception:
        raise ResumeReadError("PDF resume could not be parsed.") from None


def _load_pdf_stream(path: Path, source: Path | BytesIO) -> ResumeDocument:
    try:
        reader = PdfReader(source)
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
    """Normalize text for lookup only; never use this to rewrite stored content.

    Resume extraction and LLM output can disagree on line breaks, spacing, or
    invisible Unicode formatting characters.  Keeping only visible letters,
    numbers, and combining marks makes punctuation and layout irrelevant while
    preserving the actual textual content as evidence.
    """
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(
        char for char in normalized if char.isalnum() or unicodedata.category(char).startswith("M")
    )


def mentions_term(text: str, term: str) -> bool:
    """Return whether ``term`` occurs in ``text`` as a term, not a Latin fragment.

    Both sides are compared after :func:`normalize_text`, so casing, spacing, and
    invisible formatting characters never decide the result.

    A boundary is only required beside an ASCII alphanumeric edge.  Chinese is
    written without word separators, so ``熟悉软件测试标准…`` has to count as
    containing its own skill phrase; ``re.findall(r"\\w+")`` glues a whole Chinese
    sentence into one token and a plain word-boundary rule therefore rejects every
    embedded Chinese phrase.  The ASCII-only guard still keeps ``Java`` from
    matching inside ``JavaScript``.
    """
    needle = normalize_text(term)
    if not needle:
        return False
    raw = unicodedata.normalize("NFKC", text).casefold()
    if not raw:
        return False
    # The token form keeps Latin separators so `Jmeter/LoadRunner` stays two terms;
    # the stripped form tolerates the model disagreeing about spacing.
    candidates = (" ".join(re.findall(r"\w+", raw)), normalize_text(raw))
    return any(_bounded_contains(haystack, needle) for haystack in candidates)


def _bounded_contains(haystack: str, needle: str) -> bool:
    guard_left = _is_ascii_word(needle[0])
    guard_right = _is_ascii_word(needle[-1])
    start = 0
    while True:
        index = haystack.find(needle, start)
        if index < 0:
            return False
        end = index + len(needle)
        left_ok = not guard_left or index == 0 or not _is_ascii_word(haystack[index - 1])
        right_ok = not guard_right or end == len(haystack) or not _is_ascii_word(haystack[end])
        if left_ok and right_ok:
            return True
        start = index + 1


def _is_ascii_word(char: str) -> bool:
    return char.isascii() and char.isalnum()


def _locators_are_consecutive(left: str, right: str) -> bool:
    left_parts = left.rsplit(":", 1)
    right_parts = right.rsplit(":", 1)
    if len(left_parts) != 2 or len(right_parts) != 2:
        return False
    try:
        return left_parts[0] == right_parts[0] and int(right_parts[1]) == int(left_parts[1]) + 1
    except ValueError:
        return False
