########################################################################
#                 standards/kds/standards/constants.py                 #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Finds constants two files share, which belong in the config: a constant
one file imports from another, and the same name set to the same value
in two files. A constant is a name for a fixed value: a number, a
string, true or false, or a list, set or table of them. The config
module itself, tests and data modules are left out, since the config
is where shared values go, tests share values through their own
support module, and content is data.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import ast
import logging
import re
from collections import defaultdict
from pathlib import PurePosixPath

# Local
from kds.args import required
from kds.standards import config
from kds.standards.findings import Finding

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)
# log.debug("Takes the extension of Python files, from the config")
PYTHON = config.PYTHON_SUFFIX

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the stem of a config module, where shared values go")
CONFIG_STEM = "config"
# log.debug("Lists the folder names whose files are left out")
LEFT_OUT_DIRS = frozenset({"tests", "data"})
# log.debug("Names the import pattern's group that holds the source")
SOURCE = "source"
# log.debug("Lists the script extensions the script half reads")
SCRIPTS = (".ts", ".tsx", ".js", ".mjs", ".cjs")
# log.debug("Matches an exported script constant set to a one-line literal")
SCRIPT_CONST_RE = re.compile(
    r"^(?:export )?const ([A-Z][A-Z0-9_]*)(?::[^=]+)? = "
    r"(?P<value>'[^']*'|\"[^\"]*\"|-?\d[\d_.]*|true|false|\[[^\]]*\]|\{[^}]*\})(?: as const)?;$"
)
# log.debug("Matches the names and source of a script import")
SCRIPT_IMPORT_RE = re.compile(r"^import (?:type )?\{(?P<names>[^}]*)\} from '(?P<source>[^']+)';$")
# log.debug("Lists the functions whose call on literals still makes a literal")
LITERAL_CALLS = frozenset({"frozenset", "set", "tuple"})
# log.debug("Sets the advice every shared-constant finding gives")
ADVICE = "a value two files share belongs in the config"
# log.debug("Names the rule every finding here belongs to")
RULE = "constants"


########################################################################
#                           Shared constants                           #
########################################################################
# log.debug("Defines the shared-constant check over a whole repository")
def check_shared(
    sources: dict[str, str] | None = None, packages: frozenset[str] = frozenset()
) -> list[Finding]:
    """Flags constants that two files of one project share.

    A repository is one project, unless top-level folders are packages
    of their own, as in a library of separately installed tools: then
    each such folder is a project, and a value two of them share is
    not flagged, since neither may depend on the other for it.

    Args:
        sources: Each file's path from the root mapped to its text.
            Required.
        packages: The top-level folders that are packages of their own.

    Returns:
        A finding for each constant one file imports from another, and
        for each name set to the same value in two files.
    """
    # log.debug("Takes the sources, which the caller must give")
    sources = required(sources=sources)
    # log.debug("Groups the files the rule applies to by project")
    projects: dict[str, dict[str, str]] = defaultdict(dict)
    # log.debug("Fills the groups")
    for path, text in sources.items():
        # log.debug("Adds a file the rule applies to, under its project")
        if _applies(path):
            # log.debug("Files it under its package's folder, or the repository")
            projects[_project(path, packages)][path] = text
    # log.debug("Returns the findings of every project")
    return [f for kept in projects.values() for f in _check_project(kept)]


# log.debug("Defines which project a file belongs to")
def _project(path: str = "", packages: frozenset[str] = frozenset()) -> str:
    """Returns the folder of the package a file belongs to, or nothing.

    Args:
        path: The file's path from the repository root.
        packages: The top-level folders that are packages of their own.

    Returns:
        The file's top-level folder when it is a package, else an empty
        string for the repository as a whole.
    """
    # log.debug("Reads the file's top-level folder")
    top = PurePosixPath(path).parts[0]
    # log.debug("Returns it when it is a package of its own")
    return top if top in packages else ""


# log.debug("Defines the shared-constant check within one project")
def _check_project(kept: dict[str, str] | None = None) -> list[Finding]:
    """Flags constants two files of one project share.

    Args:
        kept: Each of the project's files mapped to its text. Required.

    Returns:
        The project's findings.
    """
    # log.debug("Takes the files, which the caller must give")
    kept = required(kept=kept)
    # log.debug("Reads every Python file's constants")
    py = {p: _python_constants(t) for p, t in kept.items() if p.endswith(PYTHON)}
    # log.debug("Reads every script's constants")
    js = {p: _script_constants(t) for p, t in kept.items() if p.endswith(SCRIPTS)}
    # log.debug("Returns the findings for both languages")
    return _findings({**py, **js}, _python_imports(kept) + _script_imports(kept))


# log.debug("Defines which files the rule reads")
def _applies(path: str | None = None) -> bool:
    """Returns whether the shared-constant rule reads a file.

    Args:
        path: The file's path from the repository root. Required.

    Returns:
        False for config modules, tests and data modules.
    """
    # log.debug("Takes the path, which the caller must give")
    path = required(path=path)
    # log.debug("Splits the path into its parts")
    parts = PurePosixPath(path)
    # log.debug("Returns whether it is none of the files left out")
    return (
        parts.stem != CONFIG_STEM
        and not LEFT_OUT_DIRS & set(parts.parts[:-1])
        and not parts.name.startswith("test_")
        and parts.name != "conftest.py"
        and ".test." not in parts.name
    )


# log.debug("Defines how a Python file's constants are read")
def _python_constants(text: str = "") -> dict[str, tuple[int, str]]:
    """Returns each top-level literal constant with its line and value.

    Args:
        text: The file's Python source.

    Returns:
        Each constant's name mapped to its line and its value's text.
    """
    # log.debug("Parses the source, giving up quietly on code that will not parse")
    try:
        # log.debug("Parses the module")
        tree = ast.parse(text)
    except SyntaxError:
        # log.debug("Returns nothing for a file the syntax rule reports")
        return {}
    # log.debug("Returns each upper-case name set to a literal")
    return {
        name: (stmt.lineno, ast.unparse(value))
        for stmt in tree.body
        for name, value in _assigned(stmt)
        if name.isupper() and not name.startswith("__") and _literal(value)
    }


# log.debug("Defines how a top-level assignment's names and value are read")
def _assigned(stmt: ast.stmt | None = None) -> list[tuple[str, ast.expr]]:
    """Returns the names a top-level assignment binds, with its value.

    Args:
        stmt: The statement. Required.

    Returns:
        Each bound name with the value, or nothing for other statements.
    """
    # log.debug("Takes the statement, which the caller must give")
    stmt = required(stmt=stmt)
    # log.debug("Reads an annotated assignment with a value")
    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and stmt.value:
        # log.debug("Returns its one name and value")
        return [(stmt.target.id, stmt.value)]
    # log.debug("Reads a plain assignment's name targets")
    if isinstance(stmt, ast.Assign):
        # log.debug("Returns each name target with the value")
        return [
            pair
            for t in stmt.targets
            for pair in (
                [(t.id, stmt.value)] if isinstance(t, ast.Name) else _unpacked(t, stmt.value)
            )
        ]
    # log.debug("Returns nothing for other statements")
    return []


# log.debug("Defines the test for a literal value")
def _literal(value: ast.expr | None = None) -> bool:
    """Returns whether a value is a literal, or a set or tuple of them.

    Args:
        value: The value's expression. Required.

    Returns:
        True for numbers, strings, booleans and collections of them.
    """
    # log.debug("Takes the value, which the caller must give")
    value = required(value=value)
    # log.debug("Unwraps frozenset, set and tuple called on a literal")
    if isinstance(value, ast.Call) and getattr(value.func, "id", None) in LITERAL_CALLS:
        # log.debug("Tests the call's one argument instead")
        return len(value.args) == 1 and not value.keywords and _literal(value.args[0])
    # log.debug("Tries to read the value as a literal")
    try:
        # log.debug("Evaluates the literal safely")
        ast.literal_eval(value)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        # log.debug("Returns false for anything that is not a literal")
        return False
    # log.debug("Returns true for a literal")
    return True


# log.debug("Defines how a script's constants are read")
def _script_constants(text: str = "") -> dict[str, tuple[int, str]]:
    """Returns each top-level one-line literal constant in a script.

    Args:
        text: The script's source.

    Returns:
        Each constant's name mapped to its line and its value's text.
    """
    # log.debug("Matches each line against the constant's form")
    matches = ((n, SCRIPT_CONST_RE.match(line)) for n, line in enumerate(text.splitlines(), 1))
    # log.debug("Returns each matched constant with its line and value")
    return {m.group(1): (n, m.group("value")) for n, m in matches if m}


# log.debug("Defines how Python imports of names are listed")
def _python_imports(sources: dict[str, str] | None = None) -> list[tuple[str, int, str, str]]:
    """Returns each name a Python file imports, with its module.

    Args:
        sources: Each kept file's path mapped to its text. Required.

    Returns:
        The importing file, the import's line, the module and the name.
    """
    # log.debug("Takes the sources, which the caller must give")
    sources = required(sources=sources)
    # log.debug("Starts with no imports")
    found: list[tuple[str, int, str, str]] = []
    # log.debug("Walks every Python file")
    for path, text in sources.items():
        # log.debug("Skips files that are not Python")
        if not path.endswith(PYTHON):
            # log.debug("Moves to the next file")
            continue
        # log.debug("Parses the file, skipping one that will not parse")
        try:
            # log.debug("Parses the module")
            tree = ast.parse(text)
        except SyntaxError:
            # log.debug("Moves to the next file")
            continue
        # log.debug("Adds each name each from-import brings in")
        found += [
            (path, node.lineno, node.module or "", alias.name)
            for node in tree.body
            if isinstance(node, ast.ImportFrom) and node.level == 0
            for alias in node.names
        ]
    # log.debug("Returns the imports")
    return found


# log.debug("Defines how script imports of names are listed")
def _script_imports(sources: dict[str, str] | None = None) -> list[tuple[str, int, str, str]]:
    """Returns each name a script imports, with the file it resolves to.

    Args:
        sources: Each kept file's path mapped to its text. Required.

    Returns:
        The importing file, the import's line, the imported file's path
        without its extension, and the name.
    """
    # log.debug("Takes the sources, which the caller must give")
    sources = required(sources=sources)
    # log.debug("Starts with no imports")
    found: list[tuple[str, int, str, str]] = []
    # log.debug("Walks every script")
    for path, text in sources.items():
        # log.debug("Skips files that are not scripts")
        if not path.endswith(SCRIPTS):
            # log.debug("Moves to the next file")
            continue
        # log.debug("Walks each one-line import of names")
        for number, line in enumerate(text.splitlines(), 1):
            # log.debug("Matches the line against the import's form")
            match = SCRIPT_IMPORT_RE.match(line)
            # log.debug("Records each name a relative import brings in")
            if match and match.group(SOURCE).startswith("."):
                # log.debug("Resolves the source against the importing file's folder")
                target = str(PurePosixPath(path).parent / match.group(SOURCE))
                # log.debug("Adds each name, dropping any alias")
                found += [
                    (path, number, _normal(target), name.split(" as ")[0].strip())
                    for name in match.group("names").split(",")
                    if name.strip()
                ]
    # log.debug("Returns the imports")
    return found


# log.debug("Defines how a resolved script path is tidied")
def _normal(target: str = "") -> str:
    """Returns a resolved import path with ./ and ../ worked out.

    Args:
        target: The importing file's folder joined with the source.

    Returns:
        The path without dots or an extension.
    """
    # log.debug("Starts with no parts")
    parts: list[str] = []
    # log.debug("Walks the path's parts")
    for part in target.split("/"):
        # log.debug("Steps up a folder for each ..")
        if part == "..":
            # log.debug("Drops the last folder")
            parts = parts[:-1]
        elif part not in (".", ""):
            # log.debug("Keeps an ordinary part")
            parts.append(part)
    # log.debug("Returns the joined path without its extension")
    return str(PurePosixPath(*parts).with_suffix("")) if parts else ""


# log.debug("Defines how the findings are drawn from constants and imports")
def _findings(
    constants: dict[str, dict[str, tuple[int, str]]] | None = None,
    imports: list[tuple[str, int, str, str]] | None = None,
) -> list[Finding]:
    """Returns a finding for each imported and each repeated constant.

    Args:
        constants: Each file's constants, by name, with line and value.
            Required.
        imports: Each imported name with its file, line and source.
            Required.

    Returns:
        The findings, one per file involved.
    """
    # log.debug("Takes the constants, which the caller must give")
    constants = required(constants=constants)
    # log.debug("Takes the imports, which the caller must give")
    imports = required(imports=imports)
    # log.debug("Starts with no findings")
    found: list[Finding] = []
    # log.debug("Walks each import, looking for one that brings in a constant")
    for path, line, source, name in imports:
        # log.debug("Finds the files that define the name as a constant")
        owners = [p for p, names in constants.items() if name in names and _matches(p, source)]
        # log.debug("Records a finding for each owner")
        found += [
            Finding(path, line, RULE, f"{name} comes from {owner}; {ADVICE}") for owner in owners
        ]
    # log.debug("Groups every file's constants by name and value")
    groups: dict[tuple[str, str], list[tuple[str, int]]] = defaultdict(list)
    # log.debug("Fills the groups")
    for path, names in constants.items():
        # log.debug("Adds each constant to its group")
        for name, (line, value) in names.items():
            # log.debug("Adds the file and line under the name and value")
            groups[(name, value)].append((path, line))
    # log.debug("Returns the import findings, plus one per file of a repeated constant")
    return found + [
        Finding(
            path, line, RULE, f"{name} is set to the same value in {len(where)} files; {ADVICE}"
        )
        for (name, _), where in groups.items()
        if len(where) > 1
        for path, line in where
    ]


# log.debug("Defines the test for a file an import's source names")
def _matches(path: str = "", source: str = "") -> bool:
    """Returns whether an import's source names a file.

    Args:
        path: The file's path from the repository root.
        source: A Python module's dotted name, or a script's resolved
            path without its extension.

    Returns:
        True when the file is the module or script the source names.
    """
    # log.debug("Writes the file's path without its extension")
    stem = str(PurePosixPath(path).with_suffix(""))
    # log.debug("Writes the same path as a dotted name, with a leading dot")
    dotted = "." + stem.replace("/", ".")
    # log.debug("Returns whether the script path or the module's dotted name matches")
    return bool(source) and (
        stem == source or dotted.endswith(f".{source}") or dotted.endswith(f".{source}.__init__")
    )


# log.debug("Defines how a tuple of names set to a tuple of values pairs up")
def _unpacked(
    target: ast.expr | None = None, value: ast.expr | None = None
) -> list[tuple[str, ast.expr]]:
    """Returns each name in a tuple target paired with its value.

    Args:
        target: The assignment's target. Required.
        value: The assignment's value. Required.

    Returns:
        Each name with the value in the same place, or nothing when the
        target and the value are not tuples of the same length.
    """
    # log.debug("Takes the target, which the caller must give")
    target = required(target=target)
    # log.debug("Takes the value, which the caller must give")
    value = required(value=value)
    # log.debug("Returns nothing unless both are tuples of the same length")
    if not (
        isinstance(target, ast.Tuple)
        and isinstance(value, ast.Tuple)
        and len(target.elts) == len(value.elts)
    ):
        # log.debug("Returns no pairs")
        return []
    # log.debug("Returns each plain name with its value")
    return [
        (name.id, item)
        for name, item in zip(target.elts, value.elts, strict=True)
        if isinstance(name, ast.Name)
    ]
