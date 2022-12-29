"""Utlity functions for general usage in Curvesim."""

import functools
import os

from dotenv import load_dotenv

from curvesim.exceptions import MissingEnvVarError

load_dotenv()


# Dummy value for optional default arg
# so that any value, including `None`,
# can be set as a default.
_NOT_VALUE = object()


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


def cache(user_function, /):
    """
    Simple lightweight unbounded cache.  Sometimes called "memoize".

    Returns the same as lru_cache(maxsize=None), creating a thin wrapper
    around a dictionary lookup for the function arguments. Because it
    never needs to evict old values, this is smaller and faster than
    lru_cache() with a size limit.

    The cache is threadsafe so the wrapped function can be used in
    multiple threads.

    ----
    This isn't in functools until python 3.9, so we copy over the
    implementation as in:
    https://github.com/python/cpython/blob/3.11/Lib/functools.py#L648
    """
    return functools.lru_cache(maxsize=None)(user_function)
