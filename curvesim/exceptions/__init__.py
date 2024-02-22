"""Contains various exceptions used in curvesim."""


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


class CurvesimTypeError(CurvesimException, TypeError):
    """Raised when an argument is the wrong type."""


class CurvesimValueError(CurvesimException, ValueError):
    """Raised when an argument has an inappropriate value (but the right type)."""


class SnapshotError(CurvesimException):
    """Error using a snapshot."""


class CalculationError(CurvesimException):
    """Error during a mathematical calculation."""


class CryptoPoolError(CurvesimException, RuntimeError):
    """Runtime error from a CryptoSwap pool."""


class MetricError(CurvesimException):
    """Error using a metric."""


class ResultsError(CurvesimException):
    """Error processing pipeline/simulation results."""


class PlotError(CurvesimException):
    """Error in plotting."""


class NetworkError(CurvesimException):
    """Error for network subpackage."""


class ApiResultError(NetworkError):
    """Raised when API results aren't as expected."""


class SimPoolError(CurvesimException):
    """Error in a SimPool operation."""


class ParameterSamplerError(CurvesimException):
    """Error using a parameter sampler."""


class StateLogError(CurvesimException):
    """Error using a state log (metrics.StateLog)."""


class UnregisteredPoolError(StateLogError):
    """Error raised when a pool type is not recognized by the metrics framework."""


class TimeSequenceError(CurvesimException):
    """Error using a TimeSequence object."""


class DataSourceError(CurvesimException):
    """Error using a DataSource object."""
