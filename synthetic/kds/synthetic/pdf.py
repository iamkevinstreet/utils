"""Build simple multi-page PDFs for test documents while recording the exact text placed on each page.

The recorded text is the ground truth for span checks: a model's quoted span must appear in the page it cites.
Rotation is supported so an "ugly scan" case can be produced without any image processing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


@dataclass
class PdfDoc:
    path: Path
    pages: list[list[str]] = field(default_factory=list)  # text lines per page, in order
    _lines: list[str] = field(default_factory=list)

    def line(self, text: str = "") -> None:
        self._lines.append(text)

    def para(self, text: str, width: int = 95) -> None:
        words = text.split()
        cur: list[str] = []
        for w in words:
            if sum(len(x) + 1 for x in cur) + len(w) > width:
                self._lines.append(" ".join(cur))
                cur = []
            cur.append(w)
        if cur:
            self._lines.append(" ".join(cur))
        self._lines.append("")

    def page_break(self) -> None:
        self.pages.append(self._lines)
        self._lines = []

    def write(self, *, rotate_pages: set[int] | None = None, font: str = "Helvetica", size: int = 10) -> Path:
        if self._lines:
            self.page_break()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        c = canvas.Canvas(str(self.path), pagesize=LETTER)
        width, height = LETTER
        leading = size * 1.4
        for idx, lines in enumerate(self.pages, start=1):
            if rotate_pages and idx in rotate_pages:
                c.setPageRotation(90)
            c.setFont(font, size)
            y = height - inch
            for text in lines:
                if y < inch:
                    c.showPage()
                    c.setFont(font, size)
                    y = height - inch
                c.drawString(inch, y, text)
                y -= leading
            c.showPage()
        c.save()
        return self.path

    def page_text(self, page_number: int) -> str:
        return "\n".join(self.pages[page_number - 1])

    def full_text(self) -> str:
        return "\n\n".join("\n".join(p) for p in self.pages)
