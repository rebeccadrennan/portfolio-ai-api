from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PDF_FILE = DATA_DIR / "LinkedinExport.pdf"

_EMAIL_PATTERN = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}\b")
_UK_PHONE_PATTERN = re.compile(r"\b(?:\+44\s?7\d{3}|(?:\(?0\)?\s?)7\d{3})\s?\d{3}\s?\d{3}\b")
_UK_POSTCODE_PATTERN = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b", re.IGNORECASE)
_ADDRESS_HINTS = (
    "street",
    "st.",
    "road",
    "rd",
    "avenue",
    "ave",
    "lane",
    "ln",
    "drive",
    "dr",
    "postcode",
    "post code",
    "flat",
    "apartment",
    "house",
)


def _read_pdf_text(pdf_path: Path) -> str:
    if not pdf_path.exists():
        return ""

    try:
        reader = PdfReader(str(pdf_path))
    except Exception:
        return ""

    pages: list[str] = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            # Skip unreadable pages rather than failing the full request.
            continue

    return "\n".join(pages).strip()


def _read_markdown_text(data_dir: Path) -> str:
    if not data_dir.exists():
        return ""

    documents: list[str] = []
    for markdown_file in sorted(data_dir.rglob("*.md")):
        try:
            content = markdown_file.read_text(encoding="utf-8")
        except Exception:
            continue

        if content.strip():
            relative_name = markdown_file.relative_to(data_dir).as_posix()
            documents.append(f"## {relative_name}\n{content.strip()}")

    return "\n\n".join(documents).strip()


def _redact_address_like_lines(text: str) -> str:
    redacted_lines: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()

        looks_like_address = bool(_UK_POSTCODE_PATTERN.search(stripped)) or (
            any(hint in lowered for hint in _ADDRESS_HINTS)
            and bool(re.search(r"\d", stripped))
            and len(stripped) <= 140
        )

        if looks_like_address:
            redacted_lines.append("[REDACTED_HOME_ADDRESS]")
        else:
            redacted_lines.append(line)

    return "\n".join(redacted_lines)


def redact_sensitive_details(text: str) -> str:
    redacted = _EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
    redacted = _UK_PHONE_PATTERN.sub("[REDACTED_PHONE]", redacted)
    redacted = _redact_address_like_lines(redacted)
    return redacted


def get_portfolio_context() -> str:
    # Markdown is the public-safe production source.
    markdown_text = _read_markdown_text(DATA_DIR)
    # LinkedIn PDF is optional and intended for local development only.
    pdf_text = _read_pdf_text(PDF_FILE)

    sections: list[str] = []
    if markdown_text:
        sections.append(f"Portfolio Knowledge Base (Markdown):\n{markdown_text}")
    if pdf_text:
        sections.append(f"Optional Local LinkedIn Export PDF:\n{pdf_text}")

    combined = "\n\n".join(sections).strip()
    if not combined:
        combined = (
            "No portfolio context is available yet. "
            "Add markdown knowledge files in app/data/ for production and optionally "
            "app/data/LinkedinExport.pdf for local development."
        )

    return redact_sensitive_details(combined)
