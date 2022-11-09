import time

from .sim import autosim


def hello_world():
    """Simple sim run as a health check."""
    t = time.time()
    res = autosim("0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7", test=True, ncpu=1)
    elapsed = time.time() - t
    print("Elapsed time:", elapsed)

    return res


if __name__ == "__main__":
    res = hello_world()
