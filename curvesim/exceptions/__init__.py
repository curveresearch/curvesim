class CurvesimException(Exception):
    """Base exception class"""


class SubgraphError(CurvesimException):
    """Raised for errors in subgraph query"""


class SubgraphResultError(SubgraphError):
    """Raised when subgraph results aren't as expected"""


class MissingEnvVarError(CurvesimException, RuntimeError):
    """Environment variable is missing."""


class CurvesimValueError(CurvesimException, ValueError):
    """Raised when an argument has an inappropriate value (but the right type)."""


class SnapshotError(CurvesimException):
    """Error using a snapshot."""
