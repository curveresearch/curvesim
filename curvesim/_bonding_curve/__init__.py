"""
Contains bonding_curve function for computing and optionally plotting a pool's
bonding curve and current reserves.
"""
from itertools import combinations

import matplotlib.pyplot as plt
from numpy import linspace

from ..pool import CurveMetaPool


def bonding_curve(pool_obj, *, truncate=0.0005, resolution=1000, show=True):
    """
    Computes and optionally plots a pool's bonding curve and current reserves.

    Parameters
    ----------
    pool_obj : CurvePool or CurveMetaPool
        A pool object to compute the bonding curve for.

    truncate : float, default=0.0001
        Determines where to truncate the bonding curve (i.e., D*truncate).

    resolution : int, default=1000
        Number of points along the bonding curve to compute.

    show : bool, default=True
        If true, plots the bonding curve.

    Returns
    -------
    xs : list of lists
        Lists of reserves for the first coin in each combination of token pairs

    ys : list of lists
        Lists of reserves for the second coin in each combination of token pairs

    """

    if isinstance(pool_obj, CurveMetaPool):
        combos = [(0, 1)]
    else:
        combos = list(combinations(range(pool_obj.n), 2))

    try:
        labels = pool_obj.metadata["coins"]["names"]
    except (AttributeError, KeyError):
        labels = [f"Coin {str(label)}" for label in range(pool_obj.n)]

    if show:
        _, axs = plt.subplots(1, len(combos), constrained_layout=True)

    D = pool_obj.D()
    xp = pool_obj._xp()

    xs_out = []
    ys_out = []
    for n, combo in enumerate(combos):
        i, j = combo

        xs_n = linspace(
            int(D * truncate), pool_obj.get_y(j, i, D * truncate, xp), resolution
        ).round()

        ys_n = []
        for x in xs_n:
            ys_n.append(pool_obj.get_y(i, j, int(x), xp))

        xs_n = [x / 10**18 for x in xs_n]
        ys_n = [y / 10**18 for y in ys_n]
        xs_out.append(xs_n)
        ys_out.append(ys_n)

        if show:
            if len(combos) == 1:
                ax = axs
            else:
                ax = axs[n]

            ax.plot(xs_n, ys_n, color="black")
            ax.scatter(xp[i] / 10**18, xp[j] / 10**18, s=40, color="black")
            ax.set_xlabel(labels[i])
            ax.set_ylabel(labels[j])

    if show:
        plt.show()

    return xs_out, ys_out
