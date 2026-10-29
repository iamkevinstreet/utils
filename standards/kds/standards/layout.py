########################################################################
#                  standards/kds/standards/layout.py                   #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Checks a repository's shape: folder depth, file  #
#                     length, required files and ignore rules.         #
########################################################################
"""The repository rules: depth, length, required files, ignores."""

from __future__ import annotations

import fnmatch
import logging
from pathlib import Path, PurePosixPath

from kds.standards.findings import Finding

# Module constants
log = logging.getLogger(__name__)
# log.debug("Sets the most folders a file may sit under")
MAX_DEPTH = 3
# log.debug("Lists the areas allowed three levels below themselves")
AREAS = ("frontend", "backend")
# log.debug("Sets the most lines a source file may have")
MAX_LINES = 500
# log.debug("Lists the extensions counted as source code")
SOURCE = (
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".mjs",
    ".cjs",
    ".astro",
    ".css",
    ".scss",
    ".sh",
    ".sql",
    ".html",
)
# log.debug("Lists the files every repository root must have")
REQUIRED = (
    "README.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "LICENSE",
    ".gitignore",
    ".gitattributes",
    ".editorconfig",
    ".pre-commit-config.yaml",
)
# log.debug("Lists the folders that must have their own README")
NEEDS_README = ("backend", "frontend", "config", "data")
# log.debug("Lists the ignore patterns every .gitignore must hold")
IGNORES = (
    ".env",
    ".env.*",
    "!.env.example",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "id_*",
    "secrets/",
    "__pycache__/",
    "*.py[cod]",
    ".venv/",
    "node_modules/",
    "dist/",
    "build/",
    "*.egg-info/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".mypy_cache/",
    "logs/",
    "*.log",
    "*.sqlite",
    "*.db",
    "data/generated/",
    ".idea/",
    ".vscode/",
    ".DS_Store",
)
# log.debug("Lists folders whose files are never checked")
SKIP_DIRS = ("vendor/", "node_modules/", "dist/", ".git/")
# log.debug("Names the rule for the file and folder layout")
RULE = "layout"
# log.debug("Sets the encoding every file is read in")
ENCODING = "utf-8"
# log.debug("Names the ignore file")
GITIGNORE = ".gitignore"


# log.debug("Defines the test for a file the checks skip")
def skipped(path: str, generated: list[str]) -> bool:
    """Return True for vendored, built and generated files."""
    # log.debug("Skips anything under a skipped folder")
    if any(path.startswith(d) or f"/{d}" in path for d in SKIP_DIRS):
        # log.debug("Returns skipped")
        return True
    # log.debug("Skips files .gitattributes marks as generated")
    return any(fnmatch.fnmatch(path, pattern) for pattern in generated)


# log.debug("Defines how generated-file patterns are read")
def generated_patterns(root: Path) -> list[str]:
    """Return the patterns .gitattributes marks linguist-generated."""
    # log.debug("Points at the repository's .gitattributes")
    attributes = root / ".gitattributes"
    # log.debug("Returns no patterns when the file is missing")
    if not attributes.is_file():
        # log.debug("Returns an empty list")
        return []
    # log.debug("Reads the file's lines")
    lines = attributes.read_text(encoding=ENCODING).splitlines()
    # log.debug("Returns the pattern of each generated line")
    return [line.split()[0] for line in lines if "linguist-generated" in line and line.split()]


# log.debug("Defines the depth rule for one file")
def check_depth(path: str) -> list[Finding]:
    """Flag a file more than three folders deep (four in an area)."""
    # log.debug("Splits the path into its folders")
    folders = PurePosixPath(path).parts[:-1]
    # log.debug("Allows one more level inside frontend/ or backend/")
    limit = MAX_DEPTH + 1 if folders and folders[0] in AREAS else MAX_DEPTH
    # log.debug("Returns a finding when the file sits too deep")
    if len(folders) > limit:
        # log.debug("Returns the depth finding")
        return [Finding(path, 0, RULE, f"{len(folders)} folders deep; at most {limit}")]
    # log.debug("Returns no findings")
    return []


# log.debug("Defines the length rule for one file")
def check_length(path: str, text: str) -> list[Finding]:
    """Flag a source file longer than 500 lines."""
    # log.debug("Counts the file's lines")
    count = len(text.splitlines())
    # log.debug("Returns a finding for a long source file")
    if path.endswith(SOURCE) and count > MAX_LINES:
        # log.debug("Returns the length finding")
        return [Finding(path, 0, RULE, f"{count} lines; split it, at most {MAX_LINES}")]
    # log.debug("Returns no findings")
    return []


# log.debug("Defines the checks on the repository as a whole")
def check_repository(root: Path, files: list[str]) -> list[Finding]:
    """Check required files, folder READMEs and ignores."""
    # log.debug("Collects the file set for quick lookups")
    present = set(files)
    # log.debug("Flags each required root file that is missing")
    found = [
        Finding(name, 0, RULE, "required at the root") for name in REQUIRED if name not in present
    ]
    # log.debug("Finds the top-level folders the repository has")
    tops = {PurePosixPath(f).parts[0] for f in files if "/" in f}
    # log.debug("Flags each folder that needs a README and lacks one")
    found += [
        Finding(f"{d}/README.md", 0, RULE, f"{d}/ needs its own README")
        for d in NEEDS_README
        if d in tops and f"{d}/README.md" not in present
    ]
    # log.debug("Adds the findings about .gitignore")
    found += _check_ignores(root)
    # log.debug("Returns every repository-level finding")
    return found


# log.debug("Defines the minimum .gitignore check")
def _check_ignores(root: Path) -> list[Finding]:
    """Flag each required ignore pattern .gitignore lacks."""
    # log.debug("Points at the repository's .gitignore")
    ignore = root / GITIGNORE
    # log.debug("Reads its patterns, or none when it is missing")
    lines = set(ignore.read_text(encoding=ENCODING).split()) if ignore.is_file() else set()
    # log.debug("Returns a finding for each missing pattern")
    return [
        Finding(GITIGNORE, 0, RULE, f"must ignore {pattern}")
        for pattern in IGNORES
        if pattern not in lines
    ]
