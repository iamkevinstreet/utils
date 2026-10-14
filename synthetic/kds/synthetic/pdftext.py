"""Read a PDF back into per-page text, the input every extraction prototype starts from."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def pages_text(path: Path | str) -> list[str]:
    reader = PdfReader(str(path))
    return [(page.extract_text() or "") for page in reader.pages]


def span_in_page(span: str, page: str) -> bool:
    """Whitespace-insensitive containment check used to verify cited spans."""
    norm = lambda s: " ".join(s.split()).casefold()  # noqa: E731
    return norm(span) in norm(page) if span.strip() else False
