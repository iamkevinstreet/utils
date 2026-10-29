########################################################################
#                     standards/tests/test_docs.py                     #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Tests the published-docs rules: which Markdown a repository may hold,
which links resolve and which break, and that code is never read as a
link.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

from pathlib import Path

# Local
from kds.standards.docs import check_docs, check_links, published

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the files a small repository holds")
FILES = {"README.md", "LICENSE", "docs/flow.svg", "backend/README.md", "backend/app/main.py"}


########################################################################
#                            Published docs                            #
########################################################################
# log.debug("Defines the test of which Markdown is published")
def test_only_readmes_changelog_security_and_data_are_published() -> None:
    """README.md anywhere, the two root docs, and data are allowed."""
    # log.debug("Checks each path")
    assert [
        published(p)
        for p in (
            "README.md",
            "backend/README.md",
            "CHANGELOG.md",
            "SECURITY.md",
            "data/sources/fact-sheet.md",
            "STYLE.md",
            "docs/plan.md",
            "docs/CHANGELOG.md",
        )
    ] == [True, True, True, True, True, False, False, False]


# log.debug("Defines the test of links that resolve")
def test_links_to_files_and_folders_held_resolve() -> None:
    """Files, folders, anchors and addresses outside are fine."""
    # log.debug("Writes links of every kind that resolves")
    text = (
        "[License](LICENSE) ![Flow](docs/flow.svg) [backend](backend/) [top](#top)\n"
        "[site](https://example.com) [mail](mailto:info@example.com) [root](./)\n"
    )
    # log.debug("Checks there are no findings")
    assert check_links("README.md", text, FILES) == []


# log.debug("Defines the test of links that break")
def test_links_to_missing_files_are_flagged() -> None:
    """A private or removed file, or a path outside, is flagged."""
    # log.debug("Links to a private doc, a missing file and outside the repository")
    text = "See [style](../STYLE.md) and [plan](../docs/plan.md).\n"
    # log.debug("Checks both are flagged from the backend README")
    assert [(f.line, f.rule) for f in check_links("backend/README.md", text, FILES)] == [
        (1, "docs"),
        (1, "docs"),
    ]


# log.debug("Defines the test that code is never read as a link")
def test_code_is_not_a_link() -> None:
    """Fenced blocks and inline code spans are skipped."""
    # log.debug("Writes a fenced block and an inline span with link-like text")
    text = "```\n[x](missing.md)\n```\nRun `[y](missing.md)` to see.\n"
    # log.debug("Checks there are no findings")
    assert check_links("README.md", text, FILES) == []


# log.debug("Defines the repository-level test")
def test_check_docs_flags_unpublished_markdown_and_broken_links(tmp_path: Path) -> None:
    """A stray doc is flagged, and a README link to a missing file.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Writes a README linking a stray doc and a missing one")
    (tmp_path / "README.md").write_text(
        "[plan](docs/plan.md) [notes](docs/notes.md)\n", encoding="utf-8"
    )
    # log.debug("Makes the docs folder")
    (tmp_path / "docs").mkdir()
    # log.debug("Writes the private doc")
    (tmp_path / "docs/plan.md").write_text("# Plan\n", encoding="utf-8")
    # log.debug("Checks both findings, the stray doc first")
    assert [(f.path, f.line) for f in check_docs(tmp_path, ["README.md", "docs/plan.md"])] == [
        ("docs/plan.md", 0),
        ("README.md", 1),
    ]
