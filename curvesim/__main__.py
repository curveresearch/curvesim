"""
Simple health check for the package.

Also provides version info from the command-line.
"""
import argparse
import platform
import time

from .sim import autosim
from .version import __version__


def hello_world():
    """Simple sim run as a health check."""
    # pylint: disable=redefined-outer-name
    t = time.time()
    res = autosim(
        "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",
        A=[100, 1000],
        fee=[3000000, 4000000],
        ncpu=1,
    )
    elapsed = time.time() - t
    print("Elapsed time:", elapsed)
    return res


def _python_info():
    """
    Return formatted string for python implementation and version.

    Returns
    --------
    str:
        Implementation name, version, and platform
    """
    impl = platform.python_implementation()
    version = platform.python_version()
    system = platform.system()
    return f"{impl} {version} on {system}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="curvesim",
        description="Simulate Curve pools in Python",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}, {_python_info()}",
    )
    args = parser.parse_args()

    # `--version` option automatically exits, so we can
    # just run this.  If other options are added, we'll
    # need to check args and decide to run or not.
    res = hello_world()
