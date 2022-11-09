class CurvesimException(Exception):
    """Base exception class"""

    pass


class SubgraphError(CurvesimException):
    """Raised for errors in subgraph query"""

    pass


class SubgraphResultError(SubgraphError):
    """Raised when subgraph results aren't as expected"""

    pass
