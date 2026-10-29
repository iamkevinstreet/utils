########################################################################
#                    synthetic/kds/synthetic/pdf.py                    #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-14
Last modified on:  2026-10-29

Builds simple PDFs and records the exact text placed on each page.
That text is the ground truth for span checks: a model's quoted span
must appear on the page it cites. Pages can be rotated, so an "ugly
scan" case needs no image processing.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

# Third-party
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

# Local
from kds.args import required

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the characters a paragraph line may hold")
LINE_WIDTH = 95
# log.debug("Sets the line spacing, as a share of the font size")
LEADING = 1.4
# log.debug("Sets the rotation of a page marked as a bad scan")
ROTATION = 90


########################################################################
#                             PDF builder                              #
########################################################################
# log.debug("Sets the default font and size")
FONT, SIZE = "Helvetica", 10


# log.debug("Defines a document being built")
@dataclass
class PdfDoc:
    """A PDF under construction: text lines grouped into pages."""

    # log.debug("Holds where the PDF is written")
    path: Path
    # log.debug("Holds each finished page's lines, in order")
    pages: list[list[str]] = field(default_factory=list)
    # log.debug("Holds the lines of the page being written")
    _lines: list[str] = field(default_factory=list)

    # log.debug("Defines adding one line")
    def line(self, text: str = "") -> None:
        """Adds a line to the current page; empty for a blank line.

        Args:
            text: The line's text.
        """
        # log.debug("Adds the line")
        self._lines.append(text)

    # log.debug("Defines adding a wrapped paragraph")
    def para(self, text: str | None = None, width: int = LINE_WIDTH) -> None:
        """Adds `text` wrapped at `width` characters, then a blank.

        Args:
            text: The paragraph's text. Required.
            width: The most characters a line may hold.
        """
        # log.debug("Takes the text, which the caller must give")
        text = required(text=text)
        # log.debug("Starts the line being filled")
        current: list[str] = []
        # log.debug("Places each word")
        for word in text.split():
            # log.debug("Starts a new line when this word would overflow")
            if sum(len(w) + 1 for w in current) + len(word) > width:
                # log.debug("Adds the full line")
                self._lines.append(" ".join(current))
                # log.debug("Empties the line being filled")
                current = []
            # log.debug("Adds the word to the line")
            current.append(word)
        # log.debug("Adds the last, partly filled line, if any")
        if current:
            # log.debug("Adds it")
            self._lines.append(" ".join(current))
        # log.debug("Ends the paragraph with a blank line")
        self._lines.append("")

    # log.debug("Defines ending a page")
    def page_break(self) -> None:
        """Finishes the current page and starts a new one."""
        # log.debug("Files the current lines as a page")
        self.pages.append(self._lines)
        # log.debug("Starts the next page empty")
        self._lines = []

    # log.debug("Defines writing the PDF")
    def write(
        self, *, rotate_pages: set[int] | None = None, font: str = FONT, size: int = SIZE
    ) -> Path:
        """Writes the PDF; pages in `rotate_pages` (from 1) turn.

        Args:
            rotate_pages: The pages to turn, as in a bad scan, by
                number from 1, if any.
            font: The font every line is drawn in.
            size: The font size, in points.

        Returns:
            The path the PDF was written to.
        """
        # log.debug("Files any unfinished page")
        if self._lines:
            # log.debug("Ends it")
            self.page_break()
        # log.debug("Creates the folder")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # log.debug("Opens a letter-size canvas")
        pdf = canvas.Canvas(str(self.path), pagesize=LETTER)
        # log.debug("Draws each page")
        for number, lines in enumerate(self.pages, start=1):
            # log.debug("Turns the page when it is marked as a bad scan")
            if rotate_pages and number in rotate_pages:
                # log.debug("Sets the rotation")
                pdf.setPageRotation(ROTATION)
            # log.debug("Draws the page's lines")
            self._draw(pdf, lines, font, size)
        # log.debug("Saves the file")
        pdf.save()
        # log.debug("Returns where it was written")
        return self.path

    # log.debug("Defines drawing one page's lines")
    @staticmethod
    def _draw(
        pdf: canvas.Canvas | None = None,
        lines: list[str] | None = None,
        font: str | None = None,
        size: int | None = None,
    ) -> None:
        """Draws lines down the page, overflowing onto a new one.

        Args:
            pdf: The canvas being drawn on. Required.
            lines: The page's lines, in order. Required.
            font: The font to draw in. Required.
            size: The font size, in points. Required.
        """
        # log.debug("Takes the pdf, which the caller must give")
        pdf = required(pdf=pdf)
        # log.debug("Takes the lines, which the caller must give")
        lines = required(lines=lines)
        # log.debug("Takes the font, which the caller must give")
        font = required(font=font)
        # log.debug("Takes the size, which the caller must give")
        size = required(size=size)
        # log.debug("Reads the page height")
        height = LETTER[1]
        # log.debug("Sets the font")
        pdf.setFont(font, size)
        # log.debug("Starts one inch from the top")
        y = height - inch
        # log.debug("Draws each line")
        for text in lines:
            # log.debug("Moves to a new page at the bottom margin")
            if y < inch:
                # log.debug("Ends the page")
                pdf.showPage()
                # log.debug("Sets the font again on the new page")
                pdf.setFont(font, size)
                # log.debug("Returns to the top")
                y = height - inch
            # log.debug("Draws the line one inch from the left")
            pdf.drawString(inch, y, text)
            # log.debug("Moves down one line")
            y -= size * LEADING
        # log.debug("Ends the page")
        pdf.showPage()

    # log.debug("Defines one page's recorded text")
    def page_text(self, page_number: int | None = None) -> str:
        """Returns the text placed on a page, counting from 1.

        Args:
            page_number: The page's number, counting from 1. Required.

        Returns:
            The page's lines, joined by newlines.
        """
        # log.debug("Takes the page number, which the caller must give")
        page_number = required(page_number=page_number)
        # log.debug("Returns the page's lines joined")
        return "\n".join(self.pages[page_number - 1])

    # log.debug("Defines the whole document's recorded text")
    def full_text(self) -> str:
        """Returns every page's text, pages separated by a blank line.

        Returns:
            The whole document's recorded text.
        """
        # log.debug("Returns all pages joined")
        return "\n\n".join("\n".join(page) for page in self.pages)
