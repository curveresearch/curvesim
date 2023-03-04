"""Package to simulate Curve pool."""
__all__ = ["autosim", "bonding_curve", "order_book", "__version__", "__version_info__"]

import numpy

from ._bonding_curve import bonding_curve
from ._order_book import order_book
from .sim import autosim
from .version import __version__, __version_info__

print(numpy.show_config())

# print("OPENBLAS_CORETYPE:", os.environ["OPENBLAS_CORETYPE"])
