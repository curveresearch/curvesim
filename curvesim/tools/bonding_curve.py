"""
Contains the bonding_curve function, which computes a pool's bonding
curve and current reserves for each pair of coins and optionally
plots the curves using Matplotlib.
"""
from itertools import combinations

import matplotlib.pyplot as plt
from numpy import linspace

from curvesim.pool import CurveMetaPool

D_UNIT = 10**18


# pylint: disable-next=too-many-locals
def bonding_curve(pool, *, truncate=0.0005, resolution=1000, plot=False):
    """
    Computes and optionally plots a pool's bonding curve and current reserves.

    Parameters
    ----------
    pool : CurvePool or CurveMetaPool
        The pool object for which the bonding curve is computed.

    truncate : float, optional (default=0.0005)
        Determines where to truncate the bonding curve. The truncation point is given
        by D*truncate, where D is the total supply of tokens in the pool.

    resolution : int, optional (default=1000)
        The number of points to compute along the bonding curve.

    plot : bool, optional (default=False)
        Plots the bonding curves using Matplotlib.

    Returns
    -------
    pair_to_curve : dict
        Dictionary with coin index pairs as keys and lists of corresponding reserves
        as values. Each list of reserves is a list of pairs, where each pair consists
        of the reserves for the first and second coin of the corresponding pair.

    Example
    --------
    >>> import curvesim
    >>> pool_address = "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"
    >>> pool = curvesim.pool.get(pool_address)
    >>> pair_to_curve = curvesim.bonding_curve(pool, plot=True)
    """

    if isinstance(pool, CurveMetaPool):
        combos = [(0, 1)]
    else:
        combos = combinations(range(pool.n), 2)

    D = pool.D()
    xp = pool._xp()  # pylint: disable=protected-access

    pair_to_curve = {}
    for (i, j) in combos:
        truncated_D = int(D * truncate)
        x_max = pool.get_y(j, i, truncated_D, xp)
        xs = linspace(truncated_D, x_max, resolution).round()

        curve = []
        for x in xs:
            y = pool.get_y(i, j, int(x), xp)
            curve.append((x, y))
        curve = [(x / D_UNIT, y / D_UNIT) for x, y in curve]
        pair_to_curve[(i, j)] = curve

    if plot:
        labels = pool.coin_names
        if not labels:
            labels = [f"Coin {str(label)}" for label in range(pool.n)]

        _plot_bonding_curve(pair_to_curve, labels, xp)

    return pair_to_curve


def _plot_bonding_curve(pair_to_curve, labels, xp):
    n = len(pair_to_curve)
    _, axs = plt.subplots(1, n, constrained_layout=True)
    if n == 1:
        axs = [axs]

    for pair, ax in zip(pair_to_curve, axs):
        curve = pair_to_curve[pair]
        xs, ys = zip(*curve)
        ax.plot(xs, ys, color="black")

        i, j = pair
        ax.scatter(xp[i] / D_UNIT, xp[j] / D_UNIT, s=40, color="black")
        ax.set_xlabel(labels[i])
        ax.set_ylabel(labels[j])

    plt.show()
