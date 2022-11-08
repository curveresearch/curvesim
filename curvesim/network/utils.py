import asyncio
import concurrent
import functools

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
            try:
                future = asyncio.run_coroutine_threadsafe(coro, loop)
                res = future.result(timeout=60)
            except concurrent.futures.TimeoutError as e:
                print("The coroutine took too long, cancelling the task...")
                future.cancel()
                raise e
            except Exception as e:
                print("The coroutine raised an exception: {!r}".format(e))
                raise e
        else:
            res = loop.run_until_complete(coro)

        return res

    return inner
