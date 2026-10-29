########################################################################
#                standards/kds/standards/pysections.py                 #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Checks what each section of a Python module holds. Imports sit under
the Imports banner (pyimports checks their groups' labels). The logger
opens the Global constants, which hold only values taken from the
project's config; other constants are local; everything else is the
logic.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import ast
import logging

# Local
from kds.args import required
from kds.standards import config, pyimports
from kds.standards import sections as sec
from kds.standards.findings import Finding

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)
# log.debug("Takes the last segment of a project's config module, from the config")
CONFIG_MODULE = config.CONFIG_MODULE

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Names the kind of a statement that imports")
IMPORT = "import"
# log.debug("Names the kind of the statement that creates the logger")
LOGGER = "logger"
# log.debug("Names the kind of a value taken from the config")
GLOBAL = "global"
# log.debug("Names the kind of a value only this file uses")
LOCAL = "local"
# log.debug("Names the kind of a type alias, allowed with constants or logic")
ALIAS = "alias"
# log.debug("Names the kind of everything else")
CODE = "code"
# log.debug("Maps each kind to the sections it may sit in")
ALLOWED = {
    IMPORT: (sec.IMPORTS,),
    LOGGER: (sec.GLOBALS,),
    GLOBAL: (sec.GLOBALS,),
    LOCAL: (sec.LOCALS,),
    ALIAS: (sec.GLOBALS, sec.LOCALS, sec.LOGIC),
    CODE: (sec.LOGIC,),
}
# log.debug("Lists the functions that create a module's logger")
LOGGER_CALLS = frozenset({"get_logger", "getLogger"})
# log.debug("Sets the package whose names count as the config")
SETTINGS_PACKAGE = "kds.settings"
# log.debug("Sets what opens and closes a dunder name")
DUNDER = "__"
# log.debug("Names the attribute a plain name's node keeps its text in")
ID = "id"


########################################################################
#                           Module sections                            #
########################################################################
# log.debug("Defines the section checks for one Python module")
def check_module(
    path: str = "",
    tree: ast.Module | None = None,
    lines: list[str] | None = None,
    banners: list[sec.Banner] | None = None,
    local_names: frozenset[str] = frozenset(),
) -> list[Finding]:
    """Checks each top-level statement sits in its section.

    Args:
        path: The file's path from the repository root.
        tree: The parsed module. Required.
        lines: The file's lines. Required.
        banners: The file's banners, in file order. Required.
        local_names: The top-level names this repository's own modules
            and packages go by.

    Returns:
        A finding for each statement out of place, each missing banner
        and each import under the wrong label.
    """
    # log.debug("Takes the tree, which the caller must give")
    tree = required(tree=tree)
    # log.debug("Takes the lines, which the caller must give")
    lines = required(lines=lines)
    # log.debug("Takes the banners, which the caller must give")
    banners = required(banners=banners)
    # log.debug("Takes the module's statements after its docstring")
    body = tree.body[1:] if ast.get_docstring(tree) is not None else tree.body
    # log.debug("Learns which names the module takes from the config")
    config = _config_names(body)
    # log.debug("Learns which names the module's own defs and classes bind")
    defined = {n.name for n in body if isinstance(n, ast.FunctionDef | ast.ClassDef)}
    # log.debug("Sorts every statement into its kind")
    kinds = [(stmt, _kind(stmt, config, defined)) for stmt in body]
    # log.debug("Checks each statement's section, then the logger's place")
    found = [f for stmt, kind in kinds for f in _check_place(path, stmt, kind, banners)]
    # log.debug("Adds the findings for the logger's place")
    found += _check_logger_first(path, kinds, banners)
    # log.debug("Lists the sections the module's statements call for")
    needs = tuple(dict.fromkeys(_needed(kind) for _, kind in kinds if _needed(kind)))
    # log.debug("Adds a finding for each section with no banner")
    found += sec.check_present(path, banners, needs)
    # log.debug("Adds the import label findings")
    found += pyimports.check_labels(
        path, [s for s, k in kinds if k == IMPORT], lines, banners, local_names
    )
    # log.debug("Returns every finding")
    return found


# log.debug("Defines the names a module takes from the config")
def _config_names(body: list[ast.stmt] | None = None) -> frozenset[str]:
    """Returns the names a module imports from the project's config.

    Args:
        body: The module's top-level statements. Required.

    Returns:
        Each name imported from a config module or from kds.settings.
    """
    # log.debug("Takes the statements, which the caller must give")
    body = required(body=body)
    # log.debug("Returns each name imported from a config module, or the module itself")
    return frozenset(
        alias.asname or alias.name
        for stmt in body
        if isinstance(stmt, ast.ImportFrom)
        for alias in stmt.names
        if _is_config(stmt.module or "") or alias.name == CONFIG_MODULE
    )


# log.debug("Defines the test for a module that is the config")
def _is_config(module: str = "") -> bool:
    """Returns whether a module path names the project's config.

    Args:
        module: The dotted module path an import names.

    Returns:
        True for a module called config and for kds.settings.
    """
    # log.debug("Returns whether the last segment is config, or it is kds.settings")
    return module.rsplit(".", 1)[-1] == CONFIG_MODULE or module.startswith(SETTINGS_PACKAGE)


# log.debug("Defines how a top-level statement is sorted into a kind")
def _kind(
    stmt: ast.stmt | None = None,
    config: frozenset[str] = frozenset(),
    defined: set[str] | None = None,
) -> str:
    """Returns the kind of a top-level statement.

    Args:
        stmt: The statement. Required.
        config: The names the module takes from the config.
        defined: The names the module's own defs and classes bind.

    Returns:
        One of the kinds: an import, the logger, a global or local
        constant, a type alias, or code.
    """
    # log.debug("Takes the statement, which the caller must give")
    stmt = required(stmt=stmt)
    # log.debug("Sorts imports, including a TYPE_CHECKING block of them")
    if isinstance(stmt, ast.Import | ast.ImportFrom) or _type_checking(stmt):
        # log.debug("Returns the import kind")
        return IMPORT
    # log.debug("Reads the names an assignment binds, if it is one")
    targets = _targets(stmt)
    # log.debug("Sorts everything that is not a plain assignment as code")
    if not targets:
        # log.debug("Returns the code kind")
        return CODE
    # log.debug("Sorts the logger's creation")
    if targets == ["log"] and _calls(stmt, LOGGER_CALLS):
        # log.debug("Returns the logger kind")
        return LOGGER
    # log.debug("Reads the names the assignment's value uses")
    used = {n.id for n in ast.walk(stmt) if isinstance(n, ast.Name)} - set(targets)
    # log.debug("Sorts the assignment by its names and what it uses")
    return _assignment_kind(targets, used, config, defined or set())


# log.debug("Defines how an assignment's kind follows from its names")
def _assignment_kind(
    targets: list[str] | None = None,
    used: set[str] | None = None,
    config: frozenset[str] = frozenset(),
    defined: set[str] | None = None,
) -> str:
    """Returns the kind of a top-level assignment.

    Args:
        targets: The names the assignment binds. Required.
        used: The names its value uses. Required.
        config: The names the module takes from the config.
        defined: The names the module's own defs and classes bind.

    Returns:
        GLOBAL when the value comes from the config, LOCAL for another
        constant, ALIAS for a type alias, CODE otherwise.
    """
    # log.debug("Takes the names, which the caller must give")
    targets = required(targets=targets)
    # log.debug("Takes the used names, which the caller must give")
    used = required(used=used)
    # log.debug("Sorts a value built on the module's own functions as code")
    if used & (defined or set()):
        # log.debug("Returns the code kind")
        return CODE
    # log.debug("Sorts a constant or dunder name by where its value comes from")
    if all(
        name.isupper() or (name.startswith(DUNDER) and name.endswith(DUNDER)) for name in targets
    ):
        # log.debug("Returns global for a value from the config, local otherwise")
        return GLOBAL if used & config else LOCAL
    # log.debug("Returns alias for a capitalised name, code for anything else")
    return ALIAS if all(name[:1].isupper() for name in targets) else CODE


# log.debug("Defines the test for a block of type-checking imports")
def _type_checking(stmt: ast.stmt | None = None) -> bool:
    """Returns whether a statement is if TYPE_CHECKING: with imports.

    Args:
        stmt: The statement. Required.

    Returns:
        True for if TYPE_CHECKING: followed only by imports.
    """
    # log.debug("Takes the statement, which the caller must give")
    stmt = required(stmt=stmt)
    # log.debug("Returns false for anything but an if statement")
    if not isinstance(stmt, ast.If):
        # log.debug("Returns no")
        return False
    # log.debug("Reads the name the condition tests")
    test = stmt.test.attr if isinstance(stmt.test, ast.Attribute) else getattr(stmt.test, ID, "")
    # log.debug("Returns whether it tests TYPE_CHECKING and only imports")
    return test == "TYPE_CHECKING" and all(
        isinstance(s, ast.Import | ast.ImportFrom) for s in stmt.body
    )


# log.debug("Defines how an assignment's bound names are read")
def _targets(stmt: ast.stmt | None = None) -> list[str]:
    """Returns the names a plain assignment binds, or nothing.

    Args:
        stmt: The statement. Required.

    Returns:
        The bound names, or an empty list when the statement is not an
        assignment to plain names.
    """
    # log.debug("Takes the statement, which the caller must give")
    stmt = required(stmt=stmt)
    # log.debug("Reads an annotated assignment's one target")
    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
        # log.debug("Returns its name")
        return [stmt.target.id]
    # log.debug("Reads a type alias statement's name")
    if isinstance(stmt, ast.TypeAlias):
        # log.debug("Returns its name")
        return [stmt.name.id]
    # log.debug("Reads a plain assignment's targets, which must all be names")
    if isinstance(stmt, ast.Assign) and all(isinstance(t, ast.Name) for t in stmt.targets):
        # log.debug("Returns the names")
        return [t.id for t in stmt.targets if isinstance(t, ast.Name)]
    # log.debug("Returns nothing for any other statement")
    return []


# log.debug("Defines the test for a statement that calls one of some names")
def _calls(stmt: ast.stmt | None = None, names: frozenset[str] = frozenset()) -> bool:
    """Returns whether a statement calls a function by one of names.

    Args:
        stmt: The statement. Required.
        names: The function names to look for.

    Returns:
        True when any call in the statement names one of them.
    """
    # log.debug("Takes the statement, which the caller must give")
    stmt = required(stmt=stmt)
    # log.debug("Returns whether a call's function name is in the set")
    return any(
        isinstance(n, ast.Call)
        and (getattr(n.func, ID, None) in names or getattr(n.func, "attr", None) in names)
        for n in ast.walk(stmt)
    )


# log.debug("Defines the check on one statement's section")
def _check_place(
    path: str = "",
    stmt: ast.stmt | None = None,
    kind: str = CODE,
    banners: list[sec.Banner] | None = None,
) -> list[Finding]:
    """Flags a statement that sits outside the sections its kind allows.

    Args:
        path: The file's path from the repository root.
        stmt: The statement. Required.
        kind: The statement's kind.
        banners: The file's banners, in file order. Required.

    Returns:
        One finding when the statement is out of place, else none.
    """
    # log.debug("Takes the statement, which the caller must give")
    stmt = required(stmt=stmt)
    # log.debug("Takes the banners, which the caller must give")
    banners = required(banners=banners)
    # log.debug("Finds the statement's first line, decorators included")
    first = min([stmt.lineno, *(d.lineno for d in getattr(stmt, "decorator_list", []))])
    # log.debug("Finds the section the statement sits in")
    banner = sec.section_of(banners, first - 1)
    # log.debug("Names that section the way ALLOWED does")
    where = (
        None if banner is None else (sec.LOGIC if banner.rank == sec.LOGIC_RANK else banner.label)
    )
    # log.debug("Returns nothing when the statement is where it belongs")
    if where in ALLOWED[kind]:
        # log.debug("Returns no findings")
        return []
    # log.debug("Returns the finding naming where it belongs")
    return [Finding(path, first, sec.RULE, _place_message(kind))]


# log.debug("Defines the message for a statement out of place")
def _place_message(kind: str = CODE) -> str:
    """Returns where a statement of a kind belongs.

    Args:
        kind: The statement's kind.

    Returns:
        The message for a statement of that kind out of place.
    """
    # log.debug("Maps each kind to the advice for it")
    advice = {
        IMPORT: "imports go under the Imports banner",
        LOGGER: "the logger opens the Global constants",
        GLOBAL: "a value from the config goes under the Global constants banner",
        LOCAL: "a constant goes under the Local constants banner; from the config, Global",
        ALIAS: "a type alias goes with the constants or the logic",
        CODE: "code goes under the banner naming the file's job",
    }
    # log.debug("Returns the advice for this kind")
    return advice[kind]


# log.debug("Defines the check that the logger opens the Global constants")
def _check_logger_first(
    path: str = "",
    kinds: list[tuple[ast.stmt, str]] | None = None,
    banners: list[sec.Banner] | None = None,
) -> list[Finding]:
    """Flags a logger that is not the Global constants' first statement.

    Args:
        path: The file's path from the repository root.
        kinds: Each top-level statement with its kind. Required.
        banners: The file's banners, in file order. Required.

    Returns:
        One finding when another statement comes before the logger.
    """
    # log.debug("Takes the statements, which the caller must give")
    kinds = required(kinds=kinds)
    # log.debug("Takes the banners, which the caller must give")
    banners = required(banners=banners)
    # log.debug("Keeps the statements in the Global constants section")
    in_globals = [
        (s, k)
        for s, k in kinds
        if (b := sec.section_of(banners, s.lineno - 1)) is not None and b.label == sec.GLOBALS
    ]
    # log.debug("Returns a finding when the first of them is not the logger")
    if any(k == LOGGER for _, k in in_globals) and in_globals[0][1] != LOGGER:
        # log.debug("Returns the finding")
        return [Finding(path, in_globals[0][0].lineno, sec.RULE, _place_message(LOGGER))]
    # log.debug("Returns no findings")
    return []


# log.debug("Defines which section a kind of statement calls for")
def _needed(kind: str = CODE) -> str:
    """Returns the section a statement of a kind needs a banner for.

    Args:
        kind: The statement's kind.

    Returns:
        The section's name, or an empty string for a type alias, which
        may sit in several.
    """
    # log.debug("Maps each kind to the one section it needs")
    needs = {IMPORT: sec.IMPORTS, LOGGER: sec.GLOBALS, GLOBAL: sec.GLOBALS, LOCAL: sec.LOCALS}
    # log.debug("Returns the section, the logic for code, nothing for an alias")
    return needs.get(kind, sec.LOGIC if kind == CODE else "")
