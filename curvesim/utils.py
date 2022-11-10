import os

from dotenv import load_dotenv

from curvesim.exceptions import MissingEnvVarError

load_dotenv()


def get_env_var(var_name):
    """
    Retrieve environment variable.

    Parameters
    ----------
    var_name: str
        Name of the environment variable.

    Returns
    -------
    str
        Value of the environment variable.

    Raise
    -----
    curvesim.exception.MissingEnvVarError
    """
    var_value = os.getenv(var_name)
    if var_value is None:
        raise MissingEnvVarError(f"Could not get env var: '{var_name}'")

    return var_value
