"""
A simulation runs trades against Curve pools, possibly a variety of
informed and noisy trades, although currently only "optimal" arbitrages
are supported.

The primary use-case is to determine optimal amplitude (A) and
fee parameters given historical price and volume feeds.
"""
from curvesim.pipelines.arbitrage import DEFAULT_PARAMS, volume_limited_arbitrage
from curvesim.pool_data import get as get_pool_data


def autosim(pool=None, chain="mainnet", pool_data=None, **kwargs):
    """
    The autosim() function simulates existing Curve pools with a range of parameters
    (e.g., the amplitude parameter, A, and/or the exchange fee). The function fetches pool
    properties (e.g., current pool size) and 2 months of price/volume data,
    runs multiple simulations in parallel, and saves results plots to the "results" directory.

    Curve pools from any chain supported by the Convex Community Subgraphs can be simulated directly
    by inputting the pool's address or symbol. For factory pools, the pool and LP token use the same
    symbol. For earlier pools, we use the LP token symbol.

    Parameters
    ----------
    pool: str, optional
        This string identifies the pool by address or LP token symbol.

        .. note::
            Either `pool` or `pool_data` must be provided.

        .. warning::
            An LP token symbol need not be unique.  In particular, factory pools
            are deployed permissionlessly and no checks are done to ensure unique
            LP token symbol.  Currently the first pool retrieved from the subgraph
            is used, which can be effectively random if token symbols clash.

    chain: str, default='mainnet'
        Identifier for blockchain or layer2.  Supported values are:
            "mainnet", "arbitrum", "optimism", "fantom", "avalanche"
            "matic", "xdai"

    pool_data: PoolData, optional
        Pool data necessary to instantiate a pool object.

        .. note::
            Either `pool` or `pool_data` must be provided.

    A: int or iterable of int, optional
        Amplification coefficient.  This controls the curvature of the
        stableswap bonding curve.  Increased values makes the curve
        flatter in a greater neighborhood of equal balances.

        Defaults to ``[int(2 ** (a / 2)) for a in range(12, 28)]``.

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

        Defaults to ``list(range(1000000, 5000000, 1000000))``.

        For basepool, use **fee_base**.

    fee_mul : int
        Fee multiplier for dynamic fee pools.

        For basepool, use **fee_mul_base**.

    admin_fee : int, default=0 * 10**9
        Fees taken for the DAO.  For factory pools, it is half of the total fees,
        as was typical for previous non-factory pools.

        Units are fixed-point percentage of `fee`, e.g. 5 * 10**9 is
        50% of the total fees.

    test: bool, default=False
        Overrides variable_params to use four test values:

        .. code-block::

            {"A": [100, 1000], "fee": [3000000, 4000000]}

    days: int, default=60
        Number of days to fetch data for.

    src: str, default='coingecko'
        Valid values for data source are 'coingecko', 'nomics', or 'local'

    data_dir: str, default='data'
        Relative path to saved data folder.

    vol_mult : float or numpy.ndarray, default computed from data
        Value(s) multiplied by market volume to specify volume limits (overrides vol_mode).

        Can be a scalar or vector with values for each pairwise coin combination

    vol_mode : int, default=1
        Modes for limiting trade volume.

        1: limits trade volumes proportionally to market volume for each pair

        2: limits trade volumes equally across pairs

        3: mode 2 for trades with meta-pool asset, mode 1 for basepool-only trades

    ncpu : int, default=4
        Number of cores to use.

    Returns
    -------
    dict
        Dictionary of results, each value being a pandas.Series.


    Raises
    ------

    Note
    ----
    """
    assert any([pool, pool_data]), "Must input 'pool' or 'pool_data'"

    pool_data = pool_data or get_pool_data(pool, chain)
    p_var, p_fixed, kwargs = _parse_arguments(**kwargs)

    results = volume_limited_arbitrage(
        pool_data, variable_params=p_var, fixed_params=p_fixed, **kwargs
    )

    return results


def _parse_arguments(**kwargs):
    pool_args = ["A", "D", "x", "p", "fee", "fee_mul", "tokens", "admin_fee"]
    basepool_args = [arg + "_base" for arg in pool_args[:-1]]

    variable_params = {}
    fixed_params = {}
    rest_of_params = {}
    defaults = DEFAULT_PARAMS.copy()

    for key, val in kwargs.items():
        if key in defaults:
            del defaults[key]

        if key in pool_args:
            if isinstance(val, int):
                fixed_params.update({key: val})

            elif all([isinstance(v, int) for v in val]):
                variable_params.update({key: val})

            else:
                raise TypeError(f"Argument {key} must be an int or iterable of ints")

        elif key in basepool_args:
            if isinstance(val, int):
                fixed_params.setdefault("basepool", {})
                fixed_params["basepool"].update({key[:-5]: val})

            elif all([isinstance(v, int) for v in val]):
                variable_params.setdefault("basepool", {})
                variable_params["basepool"].update({key[:-5]: val})

            else:
                raise TypeError(f"Argument {key} must be an int or iterable of ints")
        else:
            rest_of_params[key] = val

    variable_params = variable_params or defaults

    return variable_params, fixed_params, rest_of_params
