class CurvesimException(Exception):
    """Base exception class"""


class SubgraphError(CurvesimException):
    """Raised for errors in subgraph query"""


class SubgraphResultError(SubgraphError):
    """Raised when subgraph results aren't as expected"""


class MissingEnvVarError(CurvesimException, RuntimeError):
    """Environment variable is missing."""


class HttpClientError(CurvesimException):
    """Raised for errors from async HTTP client request."""

    def __init__(self, status, message, url=None):
        super().__init__(status, message)
        self.status = status
        self.message = message
        self.url = url

    def __repr__(self):
        return f"HttpClientError({self.status}, {self.message}, url={self.url})"


class CurvesimValueError(CurvesimException, ValueError):
    """Raised when an argument has an inappropriate value (but the right type)."""


class SnapshotError(CurvesimException):
    """Error using a snapshot."""
