"""Common or miscellaneous utility functions"""

__all__ = ["sync"]

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor

from curvesim.utils import get_event_loop

# "extra" event loop for special but important use-cases,
# such as running inside a Jupyter Notebook, which already
# runs an event loop for "convenient" await syntax.
_loop = None


def _setup_extra_event_loop():
    """Sets up the extra event loop for scheduling."""
    # pylint: disable=global-statement
    global _loop
    _loop = asyncio.new_event_loop()
    ThreadPoolExecutor().submit(_loop.run_forever)


def sync(func):
    """
    Returns a sync version of an async function.

    Parameters
    ----------
    func : callable
        An async function.

    Returns
    -------
    inner : callable
        Sync version of the async function.
    """

    @functools.wraps(func)
    def inner(*args, event_loop=None, **kwargs):
        loop = event_loop or get_event_loop()
        coro = func(*args, **kwargs)
        if loop.is_running():
            # If for some reason, we are trying to make async code
            # synchronous inside a running event loop, we are
            # probably in something like a Jupyter notebook.
            if not _loop:
                _setup_extra_event_loop()
            future = asyncio.run_coroutine_threadsafe(coro, _loop)
            res = future.result()

        else:
            res = loop.run_until_complete(coro)

        return res

    return inner
