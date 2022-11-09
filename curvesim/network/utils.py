import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor

from gmpy2 import mpz


def compute_D(xp, A):
    xp = list(map(int, xp))
    n = len(xp)
    S = sum(xp)
    Dprev = 0
    D = S
    Ann = A * n
    D = mpz(D)
    Ann = mpz(Ann)
    while abs(D - Dprev) > 1:
        D_P = D
        for x in xp:
            D_P = D_P * D // (n * x)
        Dprev = D
        D = (Ann * S + D_P * n) * D // ((Ann - 1) * D + (n + 1) * D_P)

    D = int(D)

    return D


# "extra" event loop for special but important use-cases,
# such as running inside a Jupyter Notebook, which already
# runs an event loop for "convenient" await syntax.
_loop = None


def _setupExtraEventLoop():
    """Sets up the extra event loop for scheduling."""
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
        loop = event_loop or asyncio.get_event_loop()
        coro = func(*args, **kwargs)
        if loop.is_running():
            # If for some reason, we are trying to make async code
            # synchronous inside a running event loop, we are
            # probably in something like a Jupyter notebook.
            if not _loop:
                _setupExtraEventLoop()
            future = asyncio.run_coroutine_threadsafe(coro, _loop)
            res = future.result()

        else:
            res = loop.run_until_complete(coro)

        return res

    return inner
