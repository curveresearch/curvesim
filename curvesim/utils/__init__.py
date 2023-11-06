"""Utlity functions for general usage in Curvesim."""
__all__ = [
    "get_env_var",
    "get_pairs",
    "dataclass",
    "get_event_loop",
    "cache",
    "override",
    "datetime",
    "is_address",
    "to_address",
    "Address",
]

import asyncio
import os
import sys
from dataclasses import dataclass as _dataclass
from itertools import combinations

from dotenv import load_dotenv

from curvesim.exceptions import MissingEnvVarError

from .address import Address, is_address, to_address
from .decorators import cache, override

load_dotenv()

is_py310 = sys.version_info.minor >= 10 or sys.version_info.major > 3
"""
Some utils require knowing the python version.  Right now it's only important to
distinguish between 3.10 and earlier versions.
"""

_NOT_VALUE = object()
"""
Dummy value for optional default arg
so that any value, including `None`,
can be set as a default.
"""


def get_env_var(var_name, default=_NOT_VALUE):
    """
    Retrieve environment variable.

    Parameters
    ----------
    var_name: str
        Name of the environment variable.
    default: object
        Value to return if env var is missing.

    Returns
    -------
    str
        Value of the environment variable.

    Raise
    -----
    curvesim.exception.MissingEnvVarError
        Raised if default is not set and env var is missing.
    """
    var_value = os.getenv(var_name)
    if var_value is None:
        if default is _NOT_VALUE:
            raise MissingEnvVarError(f"Could not get env var: '{var_name}'")
        return default

    return var_value


def get_pairs(arg):
    """
    Get sorted pairwise combinations of an iterable.
    Integer inputs are treated as range(int).

    Parameters
    ----------
    arg: iterable or int
        The iterable to produce pairs from, or an integer specifying the range
        to produce pairs from.

    Returns
    -------
    list
        Sorted pairwise combinations of the input.
    """
    if isinstance(arg, int):
        arg = range(arg)

    return list(combinations(arg, 2))


def dataclass(*args, **kwargs):
    """
    Slightly modified version of the standard library's `dataclass`.

    The modification is to allow the setting of slots on versions of
    python before 3.10.

    Right now, we just remove the `slots` kwarg if it exists, but in the
    future we can implement our own custom slots for old versions.
    """
    if "slots" in kwargs and not is_py310:
        del kwargs["slots"]

    return _dataclass(*args, **kwargs)


def get_event_loop():
    """
    Access the event loop without using asyncio.get_event_loop().

    Generally, you should run scheduled coroutines soon after calling
    this to avoid overwriting event loops that have unrun coroutines.

    Calling asyncio.get_event_loop() when an event loop isn't running and/or
    set will cause a DeprecationWarning in various versions of Python 3.10-3.12,
    and a future release will start raising an error instead:
    https://docs.python.org/3.11/library/asyncio-eventloop.html?highlight=selectoreventloop#asyncio.get_event_loop.

    Implementation slightly modified from https://stackoverflow.com/a/73884759
    as below works for all versions >= 3.7.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop
