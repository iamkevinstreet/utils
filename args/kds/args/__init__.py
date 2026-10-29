########################################################################
#                      args/kds/args/__init__.py                       #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Takes a function's arguments the way the code standard asks. Every
parameter has a default, None where there is no natural one, so a
function that cannot work without a value takes it with required(): it
returns the value when the caller gave it, and raises TypeError naming
the argument when the caller left it out, the same error Python raises
for a missing argument. The type checker then sees the value without
None.

mypy cannot carry a union type through required() (it widens int | str
to object), so a parameter whose type is a union is taken with a guard
instead: if value is None: raise missing(value=value). Both name the
argument from the keyword, so no string can drift from the parameter.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Lists the names the package exports")
__all__ = ["missing", "required"]


########################################################################
#                          Required arguments                          #
########################################################################
# log.debug("Defines the step that takes an argument the caller must give")
def required[T](**argument: T | None) -> T:
    """Returns an argument's value, or stops when it was left out.

    Args:
        **argument: Exactly one argument, named as in the caller's
            signature: required(notice_date=notice_date).

    Returns:
        The argument's value, which is never None.

    Raises:
        TypeError: When the value is None, or when not exactly one
            argument is given.
    """
    # log.debug("Takes the one argument's value, refusing any other call")
    value = _only(argument)
    # log.debug("Stops when the caller left the argument out")
    if value is None:
        # log.debug("Raises the same error Python raises for a missing argument")
        raise missing(**argument)
    # log.debug("Returns the value, which is never None")
    return value


# log.debug("Defines the error for an argument the caller left out")
def missing(**argument: object) -> TypeError:
    """Returns the error for an argument a caller left out, to raise.

    Args:
        **argument: Exactly one argument, named as in the caller's
            signature: raise missing(notice_date=notice_date).

    Returns:
        The TypeError Python raises for a missing argument, naming it.

    Raises:
        TypeError: When not exactly one argument is given.
    """
    # log.debug("Checks exactly one argument was passed, by name")
    _only(argument)
    # log.debug("Takes the argument's name")
    (name,) = argument
    # log.debug("Returns the error, naming the argument")
    return TypeError(f"missing required argument: {name!r}")


# log.debug("Defines the check that a call passed exactly one argument")
def _only[T](argument: dict[str, T] | None = None) -> T:
    """Returns the one value of a call that must pass exactly one.

    Args:
        argument: The call's keyword arguments. Required.

    Returns:
        The one argument's value.

    Raises:
        TypeError: When the call passed no argument or several.
    """
    # log.debug("Stops when the caller left the arguments out")
    if argument is None:
        # log.debug("Raises the missing-argument error")
        raise missing(argument=argument)
    # log.debug("Stops unless exactly one argument was passed")
    if len(argument) != 1:
        # log.debug("Raises the error for a call with no argument or several")
        raise TypeError("pass exactly one argument, by name")
    # log.debug("Returns the one value")
    return next(iter(argument.values()))
