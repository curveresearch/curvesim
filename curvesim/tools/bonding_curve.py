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

Stableswap = Union[CurvePool, CurveMetaPool, CurveRaiPool]
Cryptoswap = Union[CurveCryptoPool]

IndexPair = Tuple[int, int]
NormalizedPoint = Tuple[int, int]
Point = Tuple[float, float]


# pylint: disable-next=too-many-locals
def bonding_curve(  # noqa: C901
    pool: Union[Stableswap, Cryptoswap], *, truncate=None, resolution=1000, plot=False
) -> Dict[IndexPair, List[Point]]:
    """
    Computes and optionally plots a pool's bonding curve and current reserves.

    Parameters
    ----------
    pool : CurvePool, CurveMetaPool, CurveRaiPool, or CurveCryptoPool
        The pool object for which the bonding curve is computed.

    truncate : float, int, or None, optional (default=None)
        Determines where to truncate the bonding curve. The truncation point is given
        by D*truncate, where D is the total supply of tokens in the pool. Stableswap
        pools apply 0.0005 by default, and Cryptoswap pools apply 1 by default.

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
        combos: List[IndexPair] = [(0, 1)]
    else:
        combos = list(combinations(range(pool.n), 2))

    xp: List[int] = pool._xp()  # pylint: disable=protected-access

    if isinstance(pool, (CurveMetaPool, CurvePool, CurveRaiPool)):
        D: int = pool.D()
        if truncate is None:
            # This default value works for Stableswap, but will break Cryptoswap.
            # At this value, the graph usually cuts off cleanly around the points where
            # the Stableswap pool would depeg, as one stablecoin balance has reached
            # almost 100% of pool assets.

            truncate = 0.0005
    elif isinstance(pool, CurveCryptoPool):
        D = pool.D  # Don't recalcuate D - it will rebalance the bonding curve(s)
        if truncate is None:
            # 1 (int) "just works" for Cryptoswap. It extends the graph to the
            # point at which one coin, when valued at the price scale around which
            # liquidity is centered, is pushed to 100% of deposits `D` after starting
            # at (1 / pool.n) from the most recent rebalance. That should cover a
            # sufficient domain. The further away from (1 / pool.n) truncate is, the
            # more imbalanced the pool is at the ends of the graph.

            truncate = 1
    else:
        raise TypeError(f"Bonding curve calculation not supported for {type(pool)}")

    pair_to_curve: Dict[IndexPair, List[Point]] = {}
    current_points: Dict[IndexPair, Point] = {}
    for (i, j) in combos:
        truncated_D: int = int(D * truncate)
        x_limit: int = pool.get_y(j, i, truncated_D, xp)
        xs: List[int] = list(
            map(int, linspace(truncated_D, x_limit, resolution).round())
        )

        curve: List[Point] = []
        for x in xs:
            y: int = pool.get_y(i, j, x, xp)
            x_float, y_float = _denormalize((x, y), (i, j), pool)

            curve.append((x_float, y_float))

        pair_to_curve[(i, j)] = curve

        current_x: int = xp[i]
        current_y: int = xp[j]

        current_x_float, current_y_float = _denormalize(
            (current_x, current_y), (i, j), pool
        )

        current_points[(i, j)] = (current_x_float, current_y_float)

    if plot:
        labels: List[str] = pool.coin_names
        if not labels:
            labels = [f"Coin {str(label)}" for label in range(pool.n)]

        _plot_bonding_curve(pair_to_curve, current_points, labels)

    return pair_to_curve


def _denormalize(
    normalized_point: NormalizedPoint,
    index_pair: IndexPair,
    pool: Union[Stableswap, Cryptoswap],
) -> Point:
    """
    Converts a point made of integer balances (as if following EVM rules) to
    human-readable float form.
    """
    x, y = normalized_point
    i, j = index_pair

    assert i != j  # dev: x and y axes must use coins of different indices

    if isinstance(pool, (CurveMetaPool, CurvePool, CurveRaiPool)):
        x_factor: int = D_UNIT
        y_factor: int = D_UNIT
    elif isinstance(pool, CurveCryptoPool):
        x_factor = D_UNIT if i == 0 else pool.price_scale[i - 1]
        y_factor = D_UNIT if j == 0 else pool.price_scale[j - 1]

    x_float: float = x / x_factor
    y_float: float = y / y_factor
    point: Point = (x_float, y_float)

    return point


def _plot_bonding_curve(
    pair_to_curve: Dict[IndexPair, List[Point]],
    current_points: Dict[IndexPair, Point],
    labels: List[str],
) -> None:
    n: int = len(pair_to_curve)
    _, axs = plt.subplots(1, n, constrained_layout=True)
    if n == 1:
        axs = [axs]

    for pair, ax in zip(pair_to_curve, axs):
        curve: List[Point] = pair_to_curve[pair]
        xs, ys = zip(*curve)
        ax.plot(xs, ys, color="black")  # the entire bonding curve

        i, j = pair
        x, y = current_points[(i, j)]
        ax.scatter(x, y, s=40, color="black")  # A single dot at the current point
        ax.set_xlabel(labels[i])
        ax.set_ylabel(labels[j])

    plt.show()
