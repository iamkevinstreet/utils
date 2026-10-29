########################################################################
#                standards/kds/standards/jssections.py                 #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Checks what each section of a script holds: TypeScript, JavaScript and
an Astro component's frontmatter. Imports sit under the Imports banner,
under the standard library, third-party and local labels; an
upper-case constant set from the config sits under Global constants
and any other under Local constants; types and code are the logic. In
CSS, an @import sits under the Imports banner.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging
import re
from itertools import pairwise

# Local
from kds.args import required
from kds.standards import config, jsrules
from kds.standards import sections as sec
from kds.standards.findings import Finding

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)
# log.debug("Takes the last segment of a config module's path, from the config")
CONFIG_MODULE = config.CONFIG_MODULE
# log.debug("Takes the name of the rule every import-label finding belongs to, from the config")
IMPORT_RULE = config.IMPORT_RULE

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Matches a statement that imports or re-exports from a module")
IMPORT_RE = re.compile(r"^(?:import\b|export (?:type )?(?:\*|\{[^}]*\}) from\b)")
# log.debug("Matches the module an import names")
SOURCE_RE = re.compile(r"""(?:from\s+|^import\s+)['"]([^'"]+)['"]""")
# log.debug("Matches an upper-case constant's declaration and captures its name")
CONST_RE = re.compile(r"^(?:export )?const ([A-Z][A-Z0-9_]*)\b")
# log.debug("Matches a declaration of a type, which belongs to the logic or constants")
TYPE_RE = re.compile(r"^(?:export )?(?:declare )?(?:type|interface|enum)\b")
# log.debug("Matches the names an import brings in, braces or not")
NAMES_RE = re.compile(r"^import (?:type )?(?:(\w+)\s*,?\s*)?(?:\{([^}]*)\})?")
# log.debug("Lists Node's own modules, which count as its standard library")
NODE_MODULES = frozenset(
    {
        "assert",
        "buffer",
        "child_process",
        "crypto",
        "events",
        "fs",
        "http",
        "https",
        "module",
        "net",
        "os",
        "path",
        "process",
        "readline",
        "stream",
        "url",
        "util",
        "worker_threads",
        "zlib",
    }
)
# log.debug("Lists how a local import's source starts")
LOCAL_STARTS = (".", "/", "@/", "~/")
# log.debug("Sets the prefix of a script's label lines")
LABEL_PREFIX = "// "
# log.debug("Matches an @import rule in CSS")
CSS_IMPORT_RE = re.compile(r"^@import\b")
# log.debug("Sets how many more lines a statement other than an import may read")
STATEMENT_LINES = 8
# log.debug("Sets the message for a type above every banner")
TYPE_MESSAGE = "a type goes with the constants or the logic"


########################################################################
#                           Script sections                            #
########################################################################
# log.debug("Defines the section checks for one script")
def check_script(
    path: str = "", lines: list[str] | None = None, banners: list[sec.Banner] | None = None
) -> list[Finding]:
    """Checks every top-level statement of a script sits in its section.

    Args:
        path: The file's path from the repository root.
        lines: The file's lines. Required.
        banners: The file's banners, in file order. Required.

    Returns:
        A finding for each statement out of place, each missing banner
        and each import under the wrong label.
    """
    # log.debug("Takes the lines, which the caller must give")
    lines = required(lines=lines)
    # log.debug("Takes the banners, which the caller must give")
    banners = required(banners=banners)
    # log.debug("Reads the script's own lines: an Astro component's frontmatter")
    script = jsrules.script_lines(path, "\n".join(lines))
    # log.debug("Keeps the statements that start at the top level")
    tops = [(n, raw) for n, raw in jsrules.statement_rows(script) if raw == raw.lstrip()]
    # log.debug("Joins each statement's lines, so a long import reads as one")
    statements = [(n, _statement_text(lines, n)) for n, _ in tops]
    # log.debug("Learns which names the script takes from the config")
    config = _config_names([text for _, text in statements if IMPORT_RE.match(text)])
    # log.debug("Sorts each statement and checks its place")
    kinds = [(n, _kind(text, config)) for n, text in statements]
    # log.debug("Starts with the findings for statements out of place")
    found = [f for n, kind in kinds for f in _check_place(path, n, kind, banners)]
    # log.debug("Lists the sections the statements call for, a type calling for none")
    needs = tuple(dict.fromkeys(k for _, k in kinds if k))
    # log.debug("Adds a finding for each section with no banner")
    found += sec.check_present(path, banners, needs)
    # log.debug("Adds the import label findings")
    return found + _check_labels(
        path, lines, [(n, t) for n, t in statements if IMPORT_RE.match(t)]
    )


# log.debug("Defines how a statement's whole text is read")
def _statement_text(lines: list[str] | None = None, number: int = 1) -> str:
    """Returns a statement's text, joined up to the line that ends it.

    Args:
        lines: The file's lines. Required.
        number: The statement's first line, counted from 1.

    Returns:
        The statement's lines joined by spaces, up to a line ending in ;
        for an import, however long; any other statement reads at most
        the next eight lines.
    """
    # log.debug("Takes the lines, which the caller must give")
    lines = required(lines=lines)
    # log.debug("Starts with the statement's first line")
    parts = [lines[number - 1].strip()]
    # log.debug("Reads an import to its end, and anything else at most eight more lines")
    last = len(lines) if IMPORT_RE.match(parts[0]) else number + STATEMENT_LINES
    # log.debug("Adds lines until one ends the statement")
    for line in lines[number:last]:
        # log.debug("Stops once the statement has ended")
        if parts[-1].endswith(";") or not parts[-1].endswith(("{", ",")):
            # log.debug("Leaves the loop")
            break
        # log.debug("Adds the next line")
        parts.append(line.strip())
    # log.debug("Returns the joined text")
    return " ".join(parts)


# log.debug("Defines the names a script takes from the config")
def _config_names(imports: list[str] | None = None) -> frozenset[str]:
    """Returns the names a script imports from a config module.

    Args:
        imports: The text of each import statement. Required.

    Returns:
        The names imported from a module whose path ends in config.
    """
    # log.debug("Takes the imports, which the caller must give")
    imports = required(imports=imports)
    # log.debug("Starts with no names")
    names: set[str] = set()
    # log.debug("Walks each import")
    for text in imports:
        # log.debug("Reads the module the import names")
        source = SOURCE_RE.search(text)
        # log.debug("Skips imports that are not from a config module")
        if not source or source.group(1).rsplit("/", 1)[-1].split(".")[0] != CONFIG_MODULE:
            # log.debug("Moves to the next import")
            continue
        # log.debug("Reads the names the import brings in")
        match = NAMES_RE.match(text)
        # log.debug("Adds the default name and each braced name")
        if match:
            # log.debug("Adds the names, dropping any alias's original")
            names |= {match.group(1)} if match.group(1) else set()
            # log.debug("Adds each braced name under its local alias")
            names |= {
                n.split(" as ")[-1].strip() for n in (match.group(2) or "").split(",") if n.strip()
            }
    # log.debug("Returns the names")
    return frozenset(names)


# log.debug("Defines how a statement is sorted into the section it needs")
def _kind(text: str = "", config: frozenset[str] = frozenset()) -> str:
    """Returns the section a top-level statement belongs in.

    Args:
        text: The statement's whole text.
        config: The names the script takes from the config.

    Returns:
        The section's name; an empty string for a type, which may sit
        with the constants or the logic.
    """
    # log.debug("Sorts imports and re-exports")
    if IMPORT_RE.match(text):
        # log.debug("Returns the imports section")
        return sec.IMPORTS
    # log.debug("Sorts type declarations, which may sit in several sections")
    if TYPE_RE.match(text):
        # log.debug("Returns no one section")
        return ""
    # log.debug("Sorts upper-case constants by whether they use the config")
    if CONST_RE.match(text):
        # log.debug("Returns global for a value from the config, local otherwise")
        return sec.GLOBALS if set(re.findall(r"\b\w+\b", text)) & config else sec.LOCALS
    # log.debug("Returns the logic for everything else")
    return sec.LOGIC


# log.debug("Defines the check on one statement's section")
def _check_place(
    path: str = "", number: int = 1, kind: str = "", banners: list[sec.Banner] | None = None
) -> list[Finding]:
    """Flags a statement that sits outside the section it belongs in.

    Args:
        path: The file's path from the repository root.
        number: The statement's first line, counted from 1.
        kind: The section the statement belongs in; empty for a type.
        banners: The file's banners, in file order. Required.

    Returns:
        One finding when the statement is out of place, else none.
    """
    # log.debug("Takes the banners, which the caller must give")
    banners = required(banners=banners)
    # log.debug("Finds the section the statement sits in")
    banner = sec.section_of(banners, number - 1)
    # log.debug("Names that section the way the kinds do")
    where = (
        None if banner is None else (sec.LOGIC if banner.rank == sec.LOGIC_RANK else banner.label)
    )
    # log.debug("Lets a type sit anywhere after the imports")
    if not kind:
        # log.debug("Returns a finding only for a type above every banner or among imports")
        return (
            []
            if where not in (None, sec.IMPORTS)
            else [Finding(path, number, sec.RULE, TYPE_MESSAGE)]
        )
    # log.debug("Returns nothing when the statement is where it belongs")
    if where == kind:
        # log.debug("Returns no findings")
        return []
    # log.debug("Returns the finding naming where it belongs")
    return [
        Finding(
            path,
            number,
            sec.RULE,
            f"belongs under the {kind if kind != sec.LOGIC else 'logic'} banner",
        )
    ]


# log.debug("Defines the checks on the import groups' labels")
def _check_labels(
    path: str = "", lines: list[str] | None = None, imports: list[tuple[int, str]] | None = None
) -> list[Finding]:
    """Checks each import sits under the label of its group.

    Args:
        path: The file's path from the repository root.
        lines: The file's lines. Required.
        imports: Each import's first line and whole text. Required.

    Returns:
        A finding for each import under the wrong label or none, and
        each label out of order.
    """
    # log.debug("Takes the lines, which the caller must give")
    lines = required(lines=lines)
    # log.debug("Takes the imports, which the caller must give")
    imports = required(imports=imports)
    # log.debug("Finds each label line and its group, in file order")
    labels = [
        (i, line.removeprefix(LABEL_PREFIX))
        for i, line in enumerate(lines)
        if line.startswith(LABEL_PREFIX) and line.removeprefix(LABEL_PREFIX) in sec.GROUPS
    ]
    # log.debug("Flags labels whose groups are out of order")
    found = [
        Finding(path, i + 1, IMPORT_RULE, "import groups go: standard library, third-party, local")
        for (_, a), (i, b) in pairwise(labels)
        if sec.GROUPS.index(b) <= sec.GROUPS.index(a)
    ]
    # log.debug("Walks each import")
    for number, text in imports:
        # log.debug("Finds the label above the import, if any")
        above = next((g for i, g in reversed(labels) if i < number - 1), None)
        # log.debug("Works out which group the import belongs to")
        group = group_of(text)
        # log.debug("Flags an import under the wrong label or none")
        if above != group:
            # log.debug("Records the misplaced import")
            found.append(
                Finding(path, number, IMPORT_RULE, f"belongs under {LABEL_PREFIX}{group}")
            )
    # log.debug("Returns every finding")
    return found


# log.debug("Defines which group a script import belongs to")
def group_of(text: str = "") -> str:
    """Returns the group a script import belongs to.

    Args:
        text: The import statement's whole text.

    Returns:
        Standard library, Third-party or Local.
    """
    # log.debug("Reads the module the import names")
    match = SOURCE_RE.search(text)
    # log.debug("Takes the source, or nothing when it cannot be read")
    source = match.group(1) if match else ""
    # log.debug("Puts Node's own modules first")
    if source.startswith("node:") or source.split("/")[0] in NODE_MODULES:
        # log.debug("Returns the standard library group")
        return sec.GROUPS[0]
    # log.debug("Returns local for this repository's files, third-party otherwise")
    return sec.GROUPS[2] if source.startswith(LOCAL_STARTS) else sec.GROUPS[1]


# log.debug("Defines the check that CSS imports sit under their banner")
def check_css(
    path: str = "", lines: list[str] | None = None, banners: list[sec.Banner] | None = None
) -> list[Finding]:
    """Flags an @import outside the Imports section of a stylesheet.

    Args:
        path: The file's path from the repository root.
        lines: The file's lines. Required.
        banners: The file's banners, in file order. Required.

    Returns:
        A finding for each @import out of place.
    """
    # log.debug("Takes the lines, which the caller must give")
    lines = required(lines=lines)
    # log.debug("Takes the banners, which the caller must give")
    banners = required(banners=banners)
    # log.debug("Returns a finding for each @import not under the Imports banner")
    return [
        Finding(path, i + 1, sec.RULE, "an @import goes under the Imports banner")
        for i, line in enumerate(lines)
        if CSS_IMPORT_RE.match(line)
        and getattr(sec.section_of(banners, i), "label", None) != sec.IMPORTS
    ]
