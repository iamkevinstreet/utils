########################################################################
#                    standards/kds/standards/cli.py                    #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

The kds-standards command: checks a repository against the code
standard, stamps headers with their paths and dates, adds a header to a
new file, and switches the logger lines on and off.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import argparse
import ast
import logging
import sys
import tokenize
from pathlib import Path, PurePosixPath

# Local
from kds.args import required
from kds.standards import (
    config,
    constants,
    docs,
    jsrules,
    jssections,
    layout,
    pyfuncs,
    pylines,
    pyrules,
    pysections,
    stamp,
    toggle,
)
from kds.standards import header as hdr
from kds.standards import sections as sec
from kds.standards.findings import Finding
from kds.standards.gitdates import History, read_history, repo_files

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)
# log.debug("Takes the encoding every file is read in, from the config")
ENCODING = config.ENCODING
# log.debug("Takes the extension of Python files, from the config")
PYTHON = config.PYTHON_SUFFIX
# log.debug("Takes the script extensions the script rules read, from the config")
SCRIPTS = config.SCRIPTS

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets how bytes that are not UTF-8 are read: replaced, not fatal")
ERRORS = "replace"
# log.debug("Lists the stylesheet extensions")
STYLES = (".css", ".scss")
# log.debug("Lists the folders that are a project's two sides, not packages")
AREAS = ("backend/", "frontend/")
# log.debug("Names the folder that marks a test file")
TESTS = "tests"
# log.debug("Names the check subcommand")
CHECK = "check"
# log.debug("Names the stamp subcommand")
STAMP = "stamp"
# log.debug("Names the header subcommand")
HEADER = "header"
# log.debug("Names the state that turns logger lines on")
ON = "on"
# log.debug("Names the path argument check and trace share")
PATH = "path"


########################################################################
#                             Command line                             #
########################################################################
# log.debug("Defines the checks on one file")
def check_file(
    root: Path | None = None,
    path: str | None = None,
    history: History | None = None,
    local_names: frozenset[str] = frozenset(),
) -> list[Finding]:
    """Runs every file-level rule on one file.

    Args:
        root: The repository root. Required.
        path: The file's path from the root. Required.
        history: The repository's dates, from read_history. Required.
        local_names: The top-level names of the repository's own
            modules, for sorting Python imports into their groups.

    Returns:
        Every finding for the file.
    """
    # log.debug("Takes the root, which the caller must give")
    root = required(root=root)
    # log.debug("Takes the path, which the caller must give")
    path = required(path=path)
    # log.debug("Takes the history, which the caller must give")
    history = required(history=history)
    # log.debug("Reads the file's text")
    text = (root / path).read_text(encoding=ENCODING, errors=ERRORS)
    # log.debug("Starts with the depth and length rules")
    found = layout.check_depth(path) + layout.check_length(path, text)
    # log.debug("Finds the file's header style, if it carries one")
    style = hdr.style_for(path)
    # log.debug("Returns the layout findings for a file with no header")
    if style is None:
        # log.debug("Returns them")
        return found
    # log.debug("Finds and reads the header")
    header, problem = hdr.parse(text, style)
    # log.debug("Reports a missing or broken header, then stops: sections start after it")
    if header is None:
        # log.debug("Returns the problem with the layout findings")
        return [*found, Finding(path, 1, hdr.RULE, problem)]
    # log.debug("Adds the findings about the header's values")
    found += hdr.check_fields(header, path, history.created_on(path), history.modified_on(path))
    # log.debug("Adds the section and language rules")
    return found + _check_body(path, text, style, header.last + 1, local_names)


# log.debug("Defines the checks on everything after the header")
def _check_body(
    path: str = "",
    text: str = "",
    style: str = hdr.PYTHON,
    start: int = 0,
    local_names: frozenset[str] = frozenset(),
) -> list[Finding]:
    """Runs the section rules and the file's language rules.

    Args:
        path: The file's path from the repository root.
        text: The file's text.
        style: The file's header style.
        start: The index of the first line after the header.
        local_names: The top-level names of the repository's modules.

    Returns:
        Every finding for the sections and the language rules.
    """
    # log.debug("Splits the file into lines")
    lines = text.splitlines()
    # log.debug("Finds the banners after the header, where the file has sections")
    banners = sec.find_banners(lines, start, style) if sec.has_sections(path) else []
    # log.debug("Starts with the banners' own findings")
    found = sec.check_banners(path, banners)
    # log.debug("Adds the Python rules for Python files")
    if path.endswith(PYTHON):
        # log.debug("Adds the Python findings")
        found += _check_python(path, text, banners, local_names)
    elif path.endswith(SCRIPTS):
        # log.debug("Adds the script findings")
        found += (
            jssections.check_script(path, lines, banners)
            + jsrules.check_logger_lines(path, text)
            + jsrules.check_live(path, text)
        )
    elif path.endswith(STYLES):
        # log.debug("Adds the stylesheet findings")
        found += jssections.check_css(path, lines, banners)
    # log.debug("Returns every finding")
    return found


# log.debug("Defines the Python checks for one file")
def _check_python(
    path: str = "",
    text: str = "",
    banners: list[sec.Banner] | None = None,
    local_names: frozenset[str] = frozenset(),
) -> list[Finding]:
    """Returns the Python findings, or one if the file will not parse.

    Args:
        path: The file's path from the repository root.
        text: The file's Python source.
        banners: The file's banners, in file order. Required.
        local_names: The top-level names of the repository's modules.

    Returns:
        The section, function, logger-line, width and literal findings.
    """
    # log.debug("Takes the banners, which the caller must give")
    banners = required(banners=banners)
    # log.debug("Tries the rules that read the code")
    try:
        # log.debug("Parses the module once for the rules that read its tree")
        tree = ast.parse(text)
        # log.debug("Runs the section, function, logger-line and line rules")
        found = (
            pysections.check_module(path, tree, text.splitlines(), banners, local_names)
            + pyfuncs.check_functions(path, tree, text.splitlines())
            + pyrules.check_logger_lines(path, text)
            + pylines.check_lines(path, text)
        )
    except (SyntaxError, tokenize.TokenError) as error:
        # log.debug("Reports code that does not parse")
        return [Finding(path, getattr(error, "lineno", 0) or 0, "syntax", str(error))]
    # log.debug("Skips the literal rule for tests, which repeat values")
    if TESTS in Path(path).parts or Path(path).name.startswith("test_"):
        # log.debug("Returns the findings without the literal rule")
        return found
    # log.debug("Returns the findings with the literal rule added")
    return found + pylines.check_literals(path, text)


# log.debug("Defines how the repository's own module names are found")
def local_names_of(files: list[str] | None = None) -> frozenset[str]:
    """Returns the names the repository's own folders and modules go by.

    Args:
        files: Every file a commit would hold. Required.

    Returns:
        Each folder's name and each Python file's stem.
    """
    # log.debug("Takes the files, which the caller must give")
    files = required(files=files)
    # log.debug("Collects every folder name on every file's path")
    folders = {part for f in files for part in PurePosixPath(f).parts[:-1]}
    # log.debug("Collects every Python file's stem")
    stems = {PurePosixPath(f).stem for f in files if f.endswith(PYTHON)}
    # log.debug("Returns the names that could be imported")
    return frozenset(n for n in folders | stems if n.isidentifier())


# log.debug("Defines how the repository's own packages are found")
def packages_of(files: list[str] | None = None) -> frozenset[str]:
    """Returns the top-level folders that are packages of their own.

    Args:
        files: Every file a commit would hold. Required.

    Returns:
        Each top-level folder with its own pyproject.toml, other than a
        project's backend.
    """
    # log.debug("Takes the files, which the caller must give")
    files = required(files=files)
    # log.debug("Returns each top-level folder that holds a pyproject.toml")
    return frozenset(
        PurePosixPath(f).parts[0]
        for f in files
        if f.count("/") == 1 and f.endswith("/pyproject.toml") and not f.startswith(AREAS)
    )


# log.debug("Defines the full check of a repository")
def run_check(root: Path | None = None) -> list[Finding]:
    """Checks every file in the repository, then the repository.

    Args:
        root: The repository root. Required.

    Returns:
        Every finding, sorted by file and line.
    """
    # log.debug("Takes the root, which the caller must give")
    root = required(root=root)
    # log.debug("Reads the dates and dirty files from git")
    history = read_history(root)
    # log.debug("Lists the files a commit would hold")
    files = repo_files(root)
    # log.debug("Reads the patterns of generated files")
    generated = layout.generated_patterns(root)
    # log.debug("Keeps the files that are not skipped")
    kept = [p for p in files if not layout.skipped(p, generated)]
    # log.debug("Learns the names the repository's own modules go by")
    names = local_names_of(files)
    # log.debug("Checks each kept file")
    found = [f for p in kept for f in check_file(root, p, history, names)]
    # log.debug("Reads every source file the shared-constant rule looks at")
    sources = {
        p: (root / p).read_text(encoding=ENCODING, errors=ERRORS)
        for p in kept
        if p.endswith((PYTHON, *SCRIPTS))
    }
    # log.debug("Adds the layout, published-docs and shared-constant findings")
    found += (
        layout.check_repository(root, files)
        + docs.check_docs(root, files)
        + constants.check_shared(sources, packages_of(files))
    )
    # log.debug("Returns every finding, sorted")
    return sorted(found)


# log.debug("Defines the stamp command")
def run_stamp(root: Path | None = None, paths: list[str] | None = None) -> int:
    """Refreshes titles and dates in the given or all changed files.

    Args:
        root: The repository root. Required.
        paths: The files to stamp; every changed file when empty.

    Returns:
        The exit status: 0.
    """
    # log.debug("Takes the root, which the caller must give")
    root = required(root=root)
    # log.debug("Reads the dates and dirty files from git")
    history = read_history(root)
    # log.debug("Defaults to every changed file when none are given")
    targets = paths or sorted(history.dirty)
    # log.debug("Learns the names the repository's own modules go by")
    names = local_names_of(repo_files(root))
    # log.debug("Refreshes each file and counts the changes")
    changed = sum(stamp.refresh(root, path, history, names) for path in targets)
    # log.debug("Reports how many files changed")
    print(f"stamped {changed} file(s)")
    # log.debug("Returns success")
    return 0


# log.debug("Defines the parser for the command line")
def _parser() -> argparse.ArgumentParser:
    """Builds the argument parser with its four subcommands.

    Returns:
        The parser.
    """
    # log.debug("Creates the top-level parser")
    parser = argparse.ArgumentParser(
        prog="kds-standards", description="Hold a repository to one code standard."
    )
    # log.debug("Adds the subcommand slot")
    sub = parser.add_subparsers(dest="command", required=True)
    # log.debug("Adds check, with an optional path")
    sub.add_parser(CHECK, help="check a repository").add_argument(PATH, nargs="?", default=".")
    # log.debug("Adds stamp, with optional files")
    sub.add_parser(STAMP, help="refresh header paths and dates").add_argument("files", nargs="*")
    # log.debug("Adds header, which needs a file and a description")
    add = sub.add_parser(HEADER, help="add a header to a file")
    # log.debug("Adds the file argument to header")
    add.add_argument("file")
    # log.debug("Adds the description option to header")
    add.add_argument("--description", required=True)
    # log.debug("Adds trace, which needs on or off and a path")
    trace = sub.add_parser("trace", help="turn logger lines on or off")
    # log.debug("Adds the on or off argument")
    trace.add_argument("state", choices=[ON, "off"])
    # log.debug("Adds the path argument")
    trace.add_argument(PATH, nargs="?", default=".")
    # log.debug("Returns the finished parser")
    return parser


# log.debug("Defines the command's entry point")
def main(argv: list[str] | None = None) -> int:
    """Runs the command and returns its exit status.

    Args:
        argv: The command's arguments; the process's own when None.

    Returns:
        0 on success, 1 when check found anything or header failed.
    """
    # log.debug("Reads the arguments")
    args = _parser().parse_args(argv)
    # log.debug("Uses the current folder as the repository root")
    root = Path.cwd()
    # log.debug("Runs check and prints each finding")
    if args.command == CHECK:
        # log.debug("Collects the findings for the given path")
        found = run_check(Path(args.path).resolve())
        # log.debug("Prints every finding, one per line")
        print("\n".join(str(f) for f in found) or "kds-standards: no findings")
        # log.debug("Returns failure when anything was found")
        return 1 if found else 0
    # log.debug("Runs stamp on the given files")
    if args.command == STAMP:
        # log.debug("Returns the stamp command's status")
        return run_stamp(root, args.files)
    # log.debug("Runs header on the given file")
    if args.command == HEADER:
        # log.debug("Adds the header and keeps any error")
        error = stamp.insert(root, args.file, args.description, read_history(root))
        # log.debug("Prints the error when there is one")
        print(error or f"added a header to {args.file}")
        # log.debug("Returns failure when there was an error")
        return 1 if error else 0
    # log.debug("Runs trace and reports the files changed")
    changed = toggle.switch(Path(args.path), args.state == ON)
    # log.debug("Prints how many files were switched")
    print(f"switched {changed} file(s) {args.state}")
    # log.debug("Returns success")
    return 0


# log.debug("Runs main when the module is run as a script")
if __name__ == "__main__":
    # log.debug("Exits with main's status")
    sys.exit(main())
