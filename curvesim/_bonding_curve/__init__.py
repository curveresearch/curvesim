"""
Contains bonding_curve function for computing and optionally plotting a pool's
bonding curve and current reserves.
"""
from itertools import combinations

import matplotlib.pyplot as plt
from numpy import linspace

from curvesim.pool import CurveMetaPool


def bonding_curve(pool, *, truncate=0.0005, resolution=1000, plot=False):
    """
    Computes and optionally plots a pool's bonding curve and current reserves.

    Parameters
    ----------
    pool : CurvePool or CurveMetaPool
        A pool object to compute the bonding curve for.

    truncate : float, default=0.0001
        Determines where to truncate the bonding curve (i.e., D*truncate).

    resolution : int, default=1000
        Number of points along the bonding curve to compute.

    plot : bool, default=True
        If true, plots the bonding curve using Matplotlib.

    Returns
    -------
    xs : list of lists
        Lists of reserves for the first coin in each combination of token pairs

    ys : list of lists
        Lists of reserves for the second coin in each combination of token pairs

    """

    if isinstance(pool, CurveMetaPool):
        combos = [(0, 1)]
    else:
        combos = list(combinations(range(pool.n), 2))

    try:
        labels = pool.metadata["coins"]["names"]
    except (AttributeError, KeyError):
        labels = [f"Coin {str(label)}" for label in range(pool.n)]

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
        curve = [(x / 10**18, y / 10**18) for x, y in curve]
        pair_to_curve[(i, j)] = curve

    if plot:
        n = len(combos)
        _, axs = plt.subplots(1, n, constrained_layout=True)
        if n == 1:
            axs = [axs]

        for pair, ax in zip(combos, axs):
            curve = pair_to_curve[pair]
            xs, ys = zip(*curve)
            ax.plot(xs, ys, color="black")

            i, j = pair
            ax.scatter(xp[i] / 10**18, xp[j] / 10**18, s=40, color="black")
            ax.set_xlabel(labels[i])
            ax.set_ylabel(labels[j])

        plt.show()

    return pair_to_curve
