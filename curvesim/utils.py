import os

from dotenv import load_dotenv

from curvesim.exceptions import MissingEnvVarError

load_dotenv()


_DEFAULT = object()


def get_env_var(var_name, default=_DEFAULT):
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
        if default is _DEFAULT:
            raise MissingEnvVarError(f"Could not get env var: '{var_name}'")
        else:
            return default

    return var_value
