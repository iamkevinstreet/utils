########################################################################
#                    standards/kds/standards/cli.py                    #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           The kds-standards command: check a repository,   #
#                     stamp headers, add a header, switch tracing.     #
########################################################################
"""The kds-standards command line."""

from __future__ import annotations

import argparse
import logging
import sys
import tokenize
from pathlib import Path

from kds.standards import docs, jsrules, layout, pyrules, stamp, toggle
from kds.standards import header as hdr
from kds.standards.findings import Finding
from kds.standards.gitdates import History, read_history, repo_files

# Module constants
log = logging.getLogger(__name__)
# log.debug("Sets the encoding every file is read in")
ENCODING = "utf-8"
# log.debug("Lists the script extensions the script rules read")
SCRIPTS = (".ts", ".tsx", ".js", ".mjs", ".cjs", ".astro")
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


# log.debug("Defines the checks on one file")
def check_file(root: Path, path: str, history: History) -> list[Finding]:
    """Run every file-level rule on one file."""
    # log.debug("Reads the file's text")
    text = (root / path).read_text(encoding=ENCODING, errors="replace")
    # log.debug("Starts with the depth and length rules")
    found = layout.check_depth(path) + layout.check_length(path, text)
    # log.debug("Finds the file's header style, if it carries one")
    style = hdr.style_for(path)
    # log.debug("Checks the header when the file needs one")
    if style is not None:
        # log.debug("Adds the header findings")
        found += _check_header(path, text, style, history)
    # log.debug("Adds the Python rules for Python files")
    if path.endswith(".py"):
        # log.debug("Adds the Python findings")
        found += _check_python(path, text)
    # log.debug("Adds the script rules for script files")
    if path.endswith(SCRIPTS):
        # log.debug("Adds the logger and trace findings for scripts")
        found += jsrules.check_logger_lines(path, text) + jsrules.check_live(path, text)
    # log.debug("Returns every finding for the file")
    return found


# log.debug("Defines the header check for one file")
def _check_header(path: str, text: str, style: str, history: History) -> list[Finding]:
    """Return the header findings for one file."""
    # log.debug("Finds and reads the header box")
    found, problem = hdr.parse(text, style)
    # log.debug("Reports a missing or broken box")
    if found is None:
        # log.debug("Returns the problem as a finding")
        return [Finding(path, 1, hdr.RULE, problem)]
    # log.debug("Returns the findings about the box's values")
    return hdr.check_fields(found, path, history.created_on(path), history.modified_on(path))


# log.debug("Defines the Python checks for one file")
def _check_python(path: str, text: str) -> list[Finding]:
    """Return the Python findings, or one if the file will not parse."""
    # log.debug("Tries the rules that read the code")
    try:
        # log.debug("Runs the logger-line and line rules")
        found = pyrules.check_logger_lines(path, text) + pyrules.check_lines(path, text)
    except (SyntaxError, tokenize.TokenError) as error:
        # log.debug("Reports code that does not parse")
        return [Finding(path, getattr(error, "lineno", 0) or 0, "syntax", str(error))]
    # log.debug("Skips the literal rule for tests, which repeat values")
    if TESTS in Path(path).parts or Path(path).name.startswith("test_"):
        # log.debug("Returns the findings without the literal rule")
        return found
    # log.debug("Returns the findings with the literal rule added")
    return found + pyrules.check_literals(path, text)


# log.debug("Defines the full check of a repository")
def run_check(root: Path) -> list[Finding]:
    """Check every file in the repository, then the repository."""
    # log.debug("Reads the dates and dirty files from git")
    history = read_history(root)
    # log.debug("Lists the files a commit would hold")
    files = repo_files(root)
    # log.debug("Reads the patterns of generated files")
    generated = layout.generated_patterns(root)
    # log.debug("Checks each file that is not skipped")
    found = [
        f for p in files if not layout.skipped(p, generated) for f in check_file(root, p, history)
    ]
    # log.debug("Adds the repository's layout and published-docs findings")
    found += layout.check_repository(root, files) + docs.check_docs(root, files)
    # log.debug("Returns every finding, sorted")
    return sorted(found)


# log.debug("Defines the stamp command")
def run_stamp(root: Path, paths: list[str]) -> int:
    """Refresh titles and dates in the given or all changed files."""
    # log.debug("Reads the dates and dirty files from git")
    history = read_history(root)
    # log.debug("Defaults to every changed file when none are given")
    targets = paths or sorted(history.dirty)
    # log.debug("Refreshes each file and counts the changes")
    changed = sum(stamp.refresh(root, path, history) for path in targets)
    # log.debug("Reports how many files changed")
    print(f"stamped {changed} file(s)")
    # log.debug("Returns success")
    return 0


# log.debug("Defines the parser for the command line")
def _parser() -> argparse.ArgumentParser:
    """Build the argument parser with its four subcommands."""
    # log.debug("Creates the top-level parser")
    parser = argparse.ArgumentParser(
        prog="kds-standards", description="Hold a repository to one code standard."
    )
    # log.debug("Adds the subcommand slot")
    sub = parser.add_subparsers(dest="command", required=True)
    # log.debug("Adds check, with an optional path")
    sub.add_parser(CHECK, help="check a repository").add_argument(PATH, nargs="?", default=".")
    # log.debug("Adds stamp, with optional files")
    sub.add_parser(STAMP, help="refresh header dates").add_argument("files", nargs="*")
    # log.debug("Adds header, which needs a file and a purpose")
    add = sub.add_parser(HEADER, help="add a header to a file")
    # log.debug("Adds the file argument to header")
    add.add_argument("file")
    # log.debug("Adds the purpose option to header")
    add.add_argument("--purpose", required=True)
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
    """Run the command and return its exit status."""
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
        error = stamp.insert(root, args.file, args.purpose, read_history(root))
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
