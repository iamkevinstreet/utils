########################################################################
#                  standards/kds/standards/pyfuncs.py                  #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Checks every Python function shows its whole contract where it is
defined: each parameter has a default (None where there is no natural
one), the doc block is complete, and the parameters the doc block calls
Required are exactly those the body takes with required(), or with a
guard that raises missing() for a union-typed one. Parameters a
framework fills are left alone: pytest's tests and fixtures, FastAPI's
routes and middleware, Dash's callbacks and property setters, and any
signature a comment starting "fixed:" says a library sets.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import ast
import inspect
import logging

# Local
from kds.args import missing, required
from kds.standards import config, pydocs
from kds.standards.findings import Finding

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)
# log.debug("Takes the name of the rule every function finding belongs to, from the config")
RULE = config.FUNCTIONS_RULE

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Lists the decorator names a framework uses to fill parameters")
FRAMEWORK = frozenset(
    {
        "fixture",
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "head",
        "options",
        "trace",
        "api_route",
        "websocket",
        "middleware",
        "exception_handler",
        "on_event",
        "callback",
        "setter",
    }
)
# log.debug("Sets the comment that marks a signature a library fixes")
FIXED_MARK = "# fixed:"
# log.debug("Lists the names a method's first parameter goes by")
SELF_NAMES = ("self", "cls")
# log.debug("Sets the word that marks a parameter taken with required()")
REQUIRED_WORD = "Required."
# log.debug("Lists the calls that take an argument the caller must give")
TAKING_CALLS = frozenset({"required", "missing"})
# log.debug("Sets the prefix of a pytest test's name")
TEST_PREFIX = "test"
# log.debug("Sets the advice for a parameter with no default")
DEFAULT_ADVICE = "a default: None where there is no natural one"


########################################################################
#                            Function rules                            #
########################################################################
# log.debug("Defines the function checks for one module")
def check_functions(
    path: str = "", tree: ast.Module | None = None, lines: list[str] | None = None
) -> list[Finding]:
    """Checks every function and method in a module.

    Args:
        path: The file's path from the repository root.
        tree: The parsed module. Required.
        lines: The file's lines. Required.

    Returns:
        A finding for each missing default, each doc block problem and
        each mismatch between Required and required().
    """
    # log.debug("Takes the tree, which the caller must give")
    tree = required(tree=tree)
    # log.debug("Takes the lines, which the caller must give")
    lines = required(lines=lines)
    # log.debug("Finds every function that sits directly in a class")
    methods = {
        id(item)
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        for item in node.body
        if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    # log.debug("Starts with no findings")
    found: list[Finding] = []
    # log.debug("Walks every function in the module, nested ones included")
    for node in ast.walk(tree):
        # log.debug("Skips everything that is not a function, and overload stubs")
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) or _named(
            node, frozenset({"overload"})
        ):
            # log.debug("Moves to the next node")
            continue
        # log.debug("Lists the parameters the rules apply to")
        params = _params(node, method=id(node) in methods)
        # log.debug("Adds the default, doc block and required() findings")
        found += (
            _check_defaults(path, node, params, lines)
            + pydocs.check_doc(path, node, [name for name, _ in params])
            + _check_required(path, node, [name for name, _ in params])
        )
    # log.debug("Returns every finding")
    return found


# log.debug("Defines the parameters the rules apply to")
def _params(
    node: ast.FunctionDef | ast.AsyncFunctionDef | None = None, method: bool = False
) -> list[tuple[str, bool]]:
    """Returns each parameter's name and whether it has a default.

    A method's self or cls is left out; *args and **kwargs come with
    their stars and count as having a default, since they cannot take
    one.

    Args:
        node: The function. Required.
        method: True when the function sits directly in a class.

    Returns:
        The names, in signature order, each with whether it has a
        default.
    """
    # log.debug("Stops when the caller left out the node")
    if node is None:
        # log.debug("Raises the missing-argument error")
        raise missing(node=node)
    # log.debug("Reads the arguments")
    args = node.args
    # log.debug("Lists the positional parameters in order")
    positional = [*args.posonlyargs, *args.args]
    # log.debug("Works out where the positional defaults start")
    first_default = len(positional) - len(args.defaults)
    # log.debug("Pairs each positional parameter with whether it has a default")
    pairs = [(a.arg, i >= first_default) for i, a in enumerate(positional)]
    # log.debug("Works out whether the first parameter is self or cls")
    bound = method and not _named(node, frozenset({"staticmethod"}))
    # log.debug("Drops a method's self or cls")
    if bound and pairs and pairs[0][0] in SELF_NAMES:
        # log.debug("Removes the first parameter")
        pairs = pairs[1:]
    # log.debug("Lists *args, which cannot take a default")
    star = [(f"*{args.vararg.arg}", True)] if args.vararg else []
    # log.debug("Pairs each keyword-only parameter with whether it has a default")
    keywords = [
        (a.arg, d is not None) for a, d in zip(args.kwonlyargs, args.kw_defaults, strict=True)
    ]
    # log.debug("Lists **kwargs, which cannot take a default")
    double = [(f"**{args.kwarg.arg}", True)] if args.kwarg else []
    # log.debug("Returns every parameter in signature order")
    return pairs + star + keywords + double


# log.debug("Defines the test for a decorator by name")
def _named(
    node: ast.FunctionDef | ast.AsyncFunctionDef | None = None,
    names: frozenset[str] = frozenset(),
) -> bool:
    """Returns whether one of a function's decorators goes by a name.

    Args:
        node: The function. Required.
        names: The decorator names to look for.

    Returns:
        True when a decorator, called or not, ends in one of the names.
    """
    # log.debug("Stops when the caller left out the node")
    if node is None:
        # log.debug("Raises the missing-argument error")
        raise missing(node=node)
    # log.debug("Reads each decorator's function, unwrapping a call")
    heads = [d.func if isinstance(d, ast.Call) else d for d in node.decorator_list]
    # log.debug("Returns whether a decorator's last name is one of the names")
    return any(_last_name(h) in names for h in heads)


# log.debug("Defines how the last name of a dotted expression is read")
def _last_name(node: ast.expr | None = None) -> str:
    """Returns an attribute's name or a plain name, else nothing.

    Args:
        node: The expression. Required.

    Returns:
        The attribute's name for a.b, the name for a, else empty.
    """
    # log.debug("Takes the expression, which the caller must give")
    node = required(node=node)
    # log.debug("Returns the attribute's name")
    if isinstance(node, ast.Attribute):
        # log.debug("Returns it")
        return node.attr
    # log.debug("Returns the plain name, or nothing")
    return node.id if isinstance(node, ast.Name) else ""


# log.debug("Defines the check that every parameter has a default")
def _check_defaults(
    path: str = "",
    node: ast.FunctionDef | ast.AsyncFunctionDef | None = None,
    params: list[tuple[str, bool]] | None = None,
    lines: list[str] | None = None,
) -> list[Finding]:
    """Flags each parameter with no default, unless a framework fills.

    Args:
        path: The file's path from the repository root.
        node: The function. Required.
        params: Each parameter with whether it has a default. Required.
        lines: The file's lines. Required.

    Returns:
        A finding for each parameter without a default.
    """
    # log.debug("Stops when the caller left out the node")
    if node is None:
        # log.debug("Raises the missing-argument error")
        raise missing(node=node)
    # log.debug("Takes the parameters, which the caller must give")
    params = required(params=params)
    # log.debug("Takes the lines, which the caller must give")
    lines = required(lines=lines)
    # log.debug("Reads the signature's lines, where a fixed: comment may sit")
    signature = lines[node.lineno - 1 : node.body[0].lineno - 1]
    # log.debug("Works out whether a framework or a library sets the signature")
    exempt = (
        _named(node, FRAMEWORK)
        or node.name.startswith(TEST_PREFIX)
        or any(FIXED_MARK in line for line in signature)
    )
    # log.debug("Returns a finding for each parameter without a default")
    return [
        Finding(path, node.lineno, RULE, f"give {name} {DEFAULT_ADVICE}")
        for name, has_default in params
        if not has_default and not exempt
    ]


# log.debug("Defines the check that Required and required() agree")
def _check_required(
    path: str = "",
    node: ast.FunctionDef | ast.AsyncFunctionDef | None = None,
    names: list[str] | None = None,
) -> list[Finding]:
    """Checks Required in the doc block matches required() in the body.

    A stub, whose body is only a docstring and ..., may call a
    parameter Required for the functions that implement it.

    Args:
        path: The file's path from the repository root.
        node: The function. Required.
        names: The function's parameters, in order. Required.

    Returns:
        A finding for each parameter on only one side.
    """
    # log.debug("Stops when the caller left out the node")
    if node is None:
        # log.debug("Raises the missing-argument error")
        raise missing(node=node)
    # log.debug("Takes the names, which the caller must give")
    names = required(names=names)
    # log.debug("Reads the doc block's lines")
    lines = inspect.cleandoc(ast.get_docstring(node) or "").splitlines()
    # log.debug("Lists the parameters the doc block calls Required")
    said = {name for name, text in pydocs.entries(lines) if text.endswith(REQUIRED_WORD)}
    # log.debug("Lists the parameters the body takes with required()")
    taken = {
        keyword.arg
        for n in pydocs.own_nodes(node)
        if isinstance(n, ast.Call) and _last_name(n.func) in TAKING_CALLS
        for keyword in n.keywords
        if keyword.arg in names
        and isinstance(keyword.value, ast.Name)
        and keyword.value.id == keyword.arg
    }
    # log.debug("Lets a stub call parameters Required without taking them")
    untaken = set() if _is_stub(node) else said - taken
    # log.debug("Returns a finding for each parameter on only one side")
    return [
        Finding(path, node.lineno, RULE, f"{name} is called Required; take it with required()")
        for name in sorted(untaken)
    ] + [
        Finding(path, node.lineno, RULE, f"{name} is taken with required(); say Required.")
        for name in sorted(taken - said)
    ]


# log.debug("Defines the test for a stub that only declares a function")
def _is_stub(node: ast.FunctionDef | ast.AsyncFunctionDef | None = None) -> bool:
    """Returns whether a function's body is only a docstring and a stub.

    Args:
        node: The function. Required.

    Returns:
        True for a body of ..., pass or raise NotImplementedError after
        its docstring.
    """
    # log.debug("Stops when the caller left out the node")
    if node is None:
        # log.debug("Raises the missing-argument error")
        raise missing(node=node)
    # log.debug("Takes the statements after the docstring")
    body = node.body[1:] if ast.get_docstring(node) is not None else node.body
    # log.debug("Returns whether nothing, or one stub statement, is left")
    return not body or (
        len(body) == 1
        and (
            isinstance(body[0], ast.Pass)
            or (isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant))
            or (isinstance(body[0], ast.Raise) and "NotImplementedError" in ast.unparse(body[0]))
        )
    )
