"""
Contains the bonding_curve function, which computes a pool's bonding
curve and current reserves for each pair of coins and optionally
plots the curves using Matplotlib.
"""
from itertools import combinations
from typing import Dict, List, Tuple, Union

import matplotlib.pyplot as plt
from numpy import linspace

from curvesim.pool import CurveCryptoPool, CurveMetaPool, CurvePool, CurveRaiPool

D_UNIT = 10**18
STABLESWAP = Union[CurvePool, CurveMetaPool, CurveRaiPool]
CRYPTOSWAP = Union[CurveCryptoPool]


# pylint: disable-next=too-many-locals
def bonding_curve(  # noqa: C901
    pool: Union[STABLESWAP, CRYPTOSWAP], *, truncate=None, resolution=1000, plot=False
) -> Dict[Tuple[int, int], List[Tuple[float, float]]]:
    """
    Computes and optionally plots a pool's bonding curve and current reserves.

    Parameters
    ----------
    pool : CurvePool or CurveMetaPool
        The pool object for which the bonding curve is computed.

    truncate : Optional[float], optional (default=None)
        Determines where to truncate the bonding curve. The truncation point is given
        by D*truncate, where D is the total supply of tokens in the pool. Stableswap
        pools apply 0.0005 by default, and Cryptoswap pools apply 1.0 by default.

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
        combos: List[Tuple[int, int]] = [(0, 1)]
    else:
        combos = list(combinations(range(pool.n), 2))

    xp: List[int] = pool._xp()  # pylint: disable=protected-access

    if isinstance(pool, STABLESWAP):  # type: ignore[misc, arg-type]
        D: int = pool.D()  # type: ignore[assignment]
        if truncate is None:
            """
            This default value works for Stableswap, but will break Cryptoswap.
            At this value, the graph usually cuts off cleanly around the points where
            the Stableswap pool would depeg, as one stablecoin balance has reached
            almost 100% of pool assets.
            """
            truncate = 0.0005
    elif isinstance(pool, CRYPTOSWAP):  # type: ignore[misc, arg-type]
        D = pool.D  # Don't recalcuate D - it will rebalance the bonding curve(s)
        if truncate is None:
            """
            A 1.0 value for Cryptoswap means "extend the graph to the point where each
            x axis' max. balance is equal to total deposits D at the current price
            scale". The further away from (1 / pool.n) truncate is, the more imbalanced
            the pool is before we manage to rebalance (likely more slippage and losses).
            """
            truncate = 1.0
    else:
        raise TypeError(f"Bonding curve calculation not supported for {type(pool)}")

    pair_to_curve: Dict[Tuple[int, int], List[Tuple[float, float]]] = {}
    current_points: Dict[Tuple[int, int], Tuple[float, float]] = {}
    for (i, j) in combos:
        truncated_D: int = int(D * truncate)
        x_limit: int = pool.get_y(j, i, truncated_D, xp)
        xs: List[int] = list(linspace(truncated_D, x_limit, resolution).round())

        curve: List[Tuple[float, float]] = []
        for x in xs:
            x_float: float = x / D_UNIT
            y_float: float = pool.get_y(i, j, int(x), xp) / D_UNIT

            if isinstance(pool, CRYPTOSWAP):  # type: ignore[misc, arg-type]
                if i > 0:
                    x_float = x_float * D_UNIT / pool.price_scale[i - 1]  # type: ignore[union-attr]

                if j > 0:
                    y_float = y_float * D_UNIT / pool.price_scale[j - 1]  # type: ignore[union-attr]

            curve.append((x_float, y_float))

        pair_to_curve[(i, j)] = curve

        current_x: float = xp[i] / D_UNIT
        current_y: float = xp[j] / D_UNIT

        if isinstance(pool, CRYPTOSWAP):  # type: ignore[misc, arg-type]
            if i > 0:
                current_x = current_x * D_UNIT / pool.price_scale[i - 1]  # type: ignore[union-attr]

            if j > 0:
                current_y = current_y * D_UNIT / pool.price_scale[j - 1]  # type: ignore[union-attr]

        current_points[(i, j)] = (current_x, current_y)

    if plot:
        labels: List[str] = pool.coin_names
        if not labels:
            labels = [f"Coin {str(label)}" for label in range(pool.n)]

        _plot_bonding_curve(pair_to_curve, current_points, labels)

    return pair_to_curve


def _plot_bonding_curve(
    pair_to_curve: Dict[Tuple[int, int], List[Tuple[float, float]]],
    current_points: Dict[Tuple[int, int], Tuple[float, float]],
    labels: List[str],
) -> None:
    n: int = len(pair_to_curve)
    _, axs = plt.subplots(1, n, constrained_layout=True)
    if n == 1:
        axs = [axs]

    for pair, ax in zip(pair_to_curve, axs):
        curve: List[Tuple[float, float]] = pair_to_curve[pair]
        xs, ys = zip(*curve)
        ax.plot(xs, ys, color="black")  # the entire bonding curve

        i, j = pair
        x, y = current_points[(i, j)]
        ax.scatter(x, y, s=40, color="black")  # A single dot at the current point
        ax.set_xlabel(labels[i])
        ax.set_ylabel(labels[j])

    plt.show()
