########################################################################
#                   standards/kds/standards/docs.py                    #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Checks the docs a repository publishes: README.md files, a root
CHANGELOG.md and a root SECURITY.md, and no other Markdown. Markdown
under data/ is data, not documentation, so it may stay, and only a
README there has its links checked. Every relative link or image in a
published file must point at a file or folder the repository holds, so
nothing a visitor reads points at a private file, a removed file or a
local path.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging
import posixpath
import re
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

# Local
from kds.args import required
from kds.standards import config
from kds.standards.findings import Finding

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)
# log.debug("Takes the encoding every file is read in, from the config")
ENCODING = config.ENCODING

########################################################################
#                           Local constants                            #
########################################################################
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


########################################################################
#                            Published docs                            #
########################################################################
# log.debug("Defines the published-docs check of a repository")
def check_docs(root: Path | None = None, files: list[str] | None = None) -> list[Finding]:
    """Flags Markdown that is not published, and links that break.

    Args:
        root: The repository root. Required.
        files: Every file a commit would hold. Required.

    Returns:
        A finding for each Markdown file the repository may not
        publish, and one for each link that breaks.
    """
    # log.debug("Takes the root, which the caller must give")
    root = required(root=root)
    # log.debug("Takes the files, which the caller must give")
    files = required(files=files)
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
def published(path: str | None = None) -> bool:
    """Returns True for README.md files, the root docs and data.

    Args:
        path: The Markdown file's path from the repository root.
            Required.

    Returns:
        True when the repository may publish the file.
    """
    # log.debug("Takes the path, which the caller must give")
    path = required(path=path)
    # log.debug("Returns the verdict")
    return PurePosixPath(path).name == README or path in ROOT_DOCS or path.startswith(DATA)


# log.debug("Defines the links check for one document")
def check_links(
    path: str | None = None, text: str | None = None, present: set[str] | None = None
) -> list[Finding]:
    """Flags each relative link whose target is not in the repository.

    Args:
        path: The document's path from the repository root; relative
            links start from its folder. Required.
        text: The document's Markdown. Required.
        present: Every file the repository holds. Required.

    Returns:
        A finding for each link that breaks, on its line.
    """
    # log.debug("Takes the path, which the caller must give")
    path = required(path=path)
    # log.debug("Takes the text, which the caller must give")
    text = required(text=text)
    # log.debug("Takes the present, which the caller must give")
    present = required(present=present)
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
def _resolves(
    path: str | None = None, target: str | None = None, present: set[str] | None = None
) -> bool:
    """Returns True for an external target or a file or folder held.

    Args:
        path: The linking document's path from the repository root.
            Required.
        target: The link's target, as the document writes it. Required.
        present: Every file the repository holds. Required.

    Returns:
        True when the link resolves; False when it names nothing the
        repository holds.
    """
    # log.debug("Takes the path, which the caller must give")
    path = required(path=path)
    # log.debug("Takes the target, which the caller must give")
    target = required(target=target)
    # log.debug("Takes the present, which the caller must give")
    present = required(present=present)
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
def _is_data_file(path: str | None = None) -> bool:
    """Returns True for Markdown under data/ that is not a README.

    Args:
        path: The Markdown file's path from the repository root.
            Required.

    Returns:
        True for a data file, whose links are not checked.
    """
    # log.debug("Takes the path, which the caller must give")
    path = required(path=path)
    # log.debug("Returns the verdict")
    return path.startswith(DATA) and PurePosixPath(path).name != README
