import asyncio

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
    def inner(*args, event_loop=None, **kwargs):
        loop = event_loop or asyncio.get_event_loop()
        res = loop.run_until_complete(func(*args, **kwargs))
        return res

    return inner
