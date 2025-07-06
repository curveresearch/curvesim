"""
A simulation runs trades against Curve pools, using a strategy that may
utilize different types of informed or noise trades.

The :mod:`simulation pipeline framework <curvesim.pipelines>` allows the
user to build custom strategies for simulation.

Most users will want to use the `autosim` function, which supports
"optimal" arbitrages via the
:func:`volume-limited arbitrage pipeline <curvesim.pipelines.vol_limited_arb.pipeline>`.
The primary use-case is to determine optimal amplitude (A) and fee
parameters given historical price and volume feeds.
"""

from curvesim.logging import get_logger
from curvesim.pipelines.vol_limited_arb import pipeline as volume_limited_arbitrage
from curvesim.pool_data import get_metadata
from curvesim.utils import get_pairs

logger = get_logger(__name__)


def autosim(
    pool=None,
    chain="mainnet",
    pool_metadata=None,
    env="prod",
    **kwargs,
):
    """
    The autosim() function simulates existing Curve pools with a range of
    parameters (e.g., the amplitude parameter, A, and/or the exchange fee).

    The function fetches pool properties (e.g., current pool size) and 2
    months of price/volume data and runs multiple simulations in parallel.

    Curve pools from any chain supported by the Convex Community Subgraphs
    can be simulated directly by inputting the pool's address.

    Parameters
    ----------
    pool: str, optional
        This 0x-prefixed string identifies the pool by address.

        .. note::
            Either `pool` or `pool_metadata` must be provided.

    chain: str, default='mainnet'
        Identifier for blockchain or layer2.  Supported values are:
            "mainnet", "arbitrum", "optimism", "fantom", "avalanche"
            "matic", "xdai"

    pool_metadata: PoolMetaDataInterface, optional
        Pool state and metadata necessary to instantiate a pool object.

        .. note::
            Either `pool` or `pool_metadata` must be provided.

    A: int or iterable of int, optional
        Amplification coefficient.  This controls the curvature of the
        stableswap bonding curve.  Increased values makes the curve
        flatter in a greater neighborhood of equal balances.

        For basepool, use **A_base**.

    D: int, optional
        Total pool liquidity given in 18 decimal precision.
        Defaults to on-chain data.

        For basepool, use **D_base**.

    tokens: int, optional
        Total LP token supply.
        Defaults to on-chain data.

        For basepool, use **tokens_base**.

    fee: int or iterable of int, optional
        Fees taken for both liquidity providers and the DAO.

        Units are in fixed-point so that 10**10 is 100%,
        e.g. 4 * 10**6 is 4 bps and 2 * 10**8 is 2%.

        For basepool, use **fee_base**.

    fee_mul : int
        Fee multiplier for dynamic fee pools.

        For basepool, use **fee_mul_base**.

    admin_fee : int, default=0 * 10**9
        Fees taken for the DAO.  For factory pools, it is half of the total
        fees, as was typical for previous non-factory pools.

        Units are fixed-point percentage of `fee`, e.g. 5 * 10**9 is
        50% of the total fees.

    test: bool, default=False
        Overrides variable_params to use four test values:

        .. code-block::

            {"A": [100, 1000], "fee": [3000000, 4000000]}

    days: int, default=60
        Number of days to fetch data for.

    src: str, default='coingecko'
        Valid values for data source are 'coingecko' or 'local'

    data_dir: str, default='data'
        Relative path to saved data folder.

    vol_mult : dict, float, or int, default computed from data
        Value(s) multiplied by market volume to specify volume limits
        (overrides vol_mode).

        dict should map from trade-pair tuples to values, e.g.:

        .. code-block::

            {('DAI', 'USDC'): 0.1, ('DAI', 'USDT'): 0.1, ('USDC', 'USDT'): 0.1}

    vol_mode : int, default=1
        Modes for limiting trade volume.
        1: limits trade volumes proportionally to market volume for each pair
        2: limits trade volumes equally across pairs
        3: mode 2 for trades with meta-pool asset, mode 1 for basepool-only trades

    ncpu : int, default=os.cpu_count()
        Number of cores to use.

    env: str, default='prod'
        Environment for the Curve subgraph, which pulls pool and volume snapshots.

    Returns
    -------
    dict
        Dictionary of results, each value being a pandas.Series.
    """
    assert any([pool, pool_metadata]), "Must input 'pool' or 'pool_metadata'"

    pool_metadata = pool_metadata or get_metadata(pool, chain, env)
    p_var, p_fixed, kwargs = _parse_arguments(pool_metadata, **kwargs)

    pool_metadata = _validate_metadata(pool_metadata)

    results = volume_limited_arbitrage(
        pool_metadata,
        variable_params=p_var,
        fixed_params=p_fixed,
        **kwargs,
    )

    return results


def _validate_metadata(pool_metadata):
    coins_address = [
        "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2" if coin == "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE" else coin
        for coin in pool_metadata.coins
    ]
    coin_names = ["WETH" if name == "0xeeee" else name for name in pool_metadata.coin_names]
    pool_metadata._dict["coins"]["addresses"] = coins_address
    pool_metadata._dict["coins"]["names"] = coin_names
    return pool_metadata


def _parse_arguments(pool_metadata, **kwargs):
    pool_args = [
        "A",
        "D",
        "balances",
        "fee",
        "fee_mul",
        "tokens",
        "admin_fee",
        "gamma",
        "fee_gamma",
        "mid_fee",
        "out_fee",
    ]
    pool_args += [arg + "_base" for arg in pool_args[:-1]]

    variable_params = {}
    fixed_params = {}
    rest_of_params = {}

    for key, val in kwargs.items():
        if key in pool_args:
            if isinstance(val, int):
                fixed_params[key] = val

            elif all(isinstance(v, int) for v in val):
                variable_params[key] = val

            else:
                raise TypeError(f"Argument {key} must be an int or iterable of ints")

        elif key == "vol_mult" and isinstance(val, (int, float)):
            coin_pairs = get_pairs(pool_metadata.coin_names)
            rest_of_params[key] = dict.fromkeys(coin_pairs, val)

        else:
            rest_of_params[key] = val

    return variable_params, fixed_params, rest_of_params
