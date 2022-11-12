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
        else:
            return default

    return var_value
