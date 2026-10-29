########################################################################
#                   standards/kds/standards/docs.py                    #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Checks the published docs: only README.md,       #
#                     CHANGELOG.md and SECURITY.md, and live links.    #
########################################################################
"""The published-docs rules: which Markdown, and links that resolve.

A repository publishes README.md files, a root CHANGELOG.md and a root
SECURITY.md, and no other Markdown; Markdown under data/ is data, not
documentation. Every relative link or image in a published file must
point at a file or folder the repository holds, so nothing a visitor
reads points at a private file, a removed file or a local path.
"""

from __future__ import annotations

import logging
import posixpath
import re
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

from kds.standards.findings import Finding

# Module constants
log = logging.getLogger(__name__)
# log.debug("Names the rule")
RULE = "docs"
# log.debug("Names the README every folder may have")
README = "README.md"
# log.debug("Lists the Markdown a repository may publish at its root, besides README.md")
ROOT_DOCS = ("CHANGELOG.md", "SECURITY.md")
# log.debug("Names the folder whose Markdown is data, not documentation")
DATA = "data/"
# log.debug("Names the Markdown extension")
MARKDOWN = ".md"
# log.debug("Matches a Markdown link or image and captures its target")
LINK_RE = re.compile(r"!?\[[^\]\n]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
# log.debug("Matches an inline code span, whose text is never a link")
CODE_SPAN_RE = re.compile(r"`[^`\n]*`")
# log.debug("Marks the start or end of a fenced code block")
FENCE = "```"
# log.debug("Lists the targets that point outside the repository")
EXTERNAL = ("http://", "https://", "mailto:", "#")
# log.debug("Sets the encoding every file is read in")
ENCODING = "utf-8"


# log.debug("Defines the published-docs check of a repository")
def check_docs(root: Path, files: list[str]) -> list[Finding]:
    """Flag Markdown that is not published, and links that break."""
    # log.debug("Collects the file set for quick lookups")
    present = set(files)
    # log.debug("Lists the Markdown files")
    markdown = [f for f in files if f.endswith(MARKDOWN)]
    # log.debug("Flags each Markdown file a repository does not publish")
    found = [
        Finding(f, 0, RULE, "only README.md, CHANGELOG.md and SECURITY.md are published")
        for f in markdown
        if not published(f)
    ]
    # log.debug("Checks the links in each published document")
    for path in markdown:
        # log.debug("Skips data files and anything not published")
        if published(path) and not _is_data_file(path):
            # log.debug("Adds the file's broken links")
            found += check_links(path, (root / path).read_text(encoding=ENCODING), present)
    # log.debug("Returns every finding")
    return found


# log.debug("Defines which Markdown a repository publishes")
def published(path: str) -> bool:
    """Return True for README.md files, the root docs and data."""
    # log.debug("Returns the verdict")
    return PurePosixPath(path).name == README or path in ROOT_DOCS or path.startswith(DATA)


# log.debug("Defines the links check for one document")
def check_links(path: str, text: str, present: set[str]) -> list[Finding]:
    """Flag each relative link in `text` whose target is not present."""
    # log.debug("Starts outside a fenced code block")
    fenced = False
    # log.debug("Starts with no findings")
    found: list[Finding] = []
    # log.debug("Reads the document line by line")
    for number, line in enumerate(text.splitlines(), start=1):
        # log.debug("Toggles at each fence; code is never a link")
        if line.lstrip().startswith(FENCE):
            # log.debug("Flips the fenced state")
            fenced = not fenced
            # log.debug("Moves to the next line")
            continue
        # log.debug("Skips lines inside a fence")
        if fenced:
            # log.debug("Moves to the next line")
            continue
        # log.debug("Checks each link outside inline code")
        for target in LINK_RE.findall(CODE_SPAN_RE.sub("", line)):
            # log.debug("Flags a target the repository does not hold")
            if not _resolves(path, target, present):
                # log.debug("Adds the finding")
                found.append(
                    Finding(path, number, RULE, f"links to {target}, which is not in the repo")
                )
    # log.debug("Returns the findings")
    return found


# log.debug("Defines whether one link target resolves")
def _resolves(path: str, target: str, present: set[str]) -> bool:
    """Return True for an external target or a file or folder held."""
    # log.debug("Trusts addresses outside the repository and in-page anchors")
    if target.startswith(EXTERNAL):
        # log.debug("Returns resolved")
        return True
    # log.debug("Drops any anchor or query, and decodes the path")
    relative = unquote(target.split("#", 1)[0].split("?", 1)[0])
    # log.debug("Joins it to the document's folder, or the root for a leading slash")
    base = "" if relative.startswith("/") else str(PurePosixPath(path).parent)
    # log.debug("Normalises the path to the repository's form")
    joined = posixpath.normpath(posixpath.join(base, relative.lstrip("/")))
    # log.debug("Returns True for the root, a file held, or a folder holding files")
    return joined == "." or joined in present or any(f.startswith(f"{joined}/") for f in present)


# log.debug("Defines the test for a data file, whose links are not ours")
def _is_data_file(path: str) -> bool:
    """Return True for Markdown under data/ that is not a README."""
    # log.debug("Returns the verdict")
    return path.startswith(DATA) and PurePosixPath(path).name != README
