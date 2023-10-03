from eth_utils import to_checksum_address

from curvesim.utils import get_event_loop

from ..network.curve_prices import get_pool_parameters
from ..network.subgraph import get_pool_info, get_pool_reserves, symbol_address_sync
from ..network.web3 import underlying_coin_info_sync


def from_address(address, chain, env="prod", end_ts=None):
    """
    Fetches pool metadata (pool info, parameters, & reserves).

    Parameters
    ----------
    address: str
        Address prefixed with '0x'
    chain: str
        Chain name
    env: str
        Environment name for subgraph: 'prod' or 'staging'

    Returns
    -------
    Pool metadata dictionary as used by :class:`PoolMetaDataInterface`.
    """
    loop = get_event_loop()
    pool_info = get_pool_info(address, chain, env=env, event_loop=loop)
    params = get_pool_parameters(address, chain, end_ts=end_ts, event_loop=loop)
    reserves = get_pool_reserves(
        address, chain, env=env, end_ts=end_ts, event_loop=loop
    )

    return _process_pool_data(pool_info, params, reserves, chain, env, end_ts, loop)


def from_symbol(symbol, chain, env):
    address = symbol_address_sync(symbol, chain)
    data = from_address(address, chain, env)
    return data


def _process_pool_data(pool_info, params, reserves, chain, env, end_ts, loop):
    pool_info = _process_pool_info(pool_info, chain, env, end_ts, loop)
    params = _process_params(params, pool_info["version"])
    reserves = _process_reserves(reserves)

    return {**pool_info, "params": params, "reserves": reserves}


def _process_pool_info(pool_info, chain, env, end_ts, loop):
    version = 2 if pool_info["isV2"] else 1
    coins = _process_coin_info(pool_info, loop)
    basepool = _get_basepool_data(pool_info, chain, env, end_ts)

    return {
        "name": pool_info["name"],
        "address": to_checksum_address(pool_info["address"]),
        "chain": chain,
        "symbol": pool_info["symbol"].strip(),
        "version": version,
        "pool_type": pool_info["poolType"],
        "coins": coins,
        "basepool": basepool,
    }


def _process_coin_info(pool_info, loop):
    coins = {
        "names": pool_info["coinNames"],
        "addresses": [to_checksum_address(a) for a in pool_info["coins"]],
        "decimals": [int(d) for d in pool_info["coinDecimals"]],
    }

    # Get underlying token addresses for lending pools
    if pool_info["poolType"] == "LENDING":
        names = [n[1:] for n in coins["names"]]
        u_addrs, u_decs = underlying_coin_info_sync(coins["addresses"], event_loop=loop)

        coins = {
            "names": names,
            "addresses": u_addrs,
            "decimals": u_decs,
            "wrapper": coins,
        }

    return coins


def _get_basepool_data(pool_info, chain, env, end_ts):
    if not pool_info["metapool"]:
        return None

    return from_address(pool_info["basePool"], chain, env=env, end_ts=end_ts)


def _process_params(params, version):
    if version == 1:
        fee_mul = params["offpeg_fee_multiplier"]
        return {
            "A": int(params["a"]),
            "fee": int(params["fee"]),
            "fee_mul": int(fee_mul) if fee_mul else None,
            "admin_fee": int(params["admin_fee"]),
            "timestamp": int(params["timestamp"]),
        }

    if version == 2:
        return {
            "A": int(params["a"]),
            "gamma": int(params["gamma"]),
            "fee_gamma": int(params["fee_gamma"]),
            "mid_fee": int(params["mid_fee"]),
            "out_fee": int(params["out_fee"]),
            "allowed_extra_profit": int(params["allowed_extra_profit"]),
            "adjustment_step": int(params["adjustment_step"]),
            "ma_half_time": int(params["ma_half_time"]),
            "price_scale": [int(p) for p in params["price_scale"]],
            "price_oracle": [int(p) for p in params["price_oracle"]],
            # "last_prices": [int(p) for p in params["last_prices"]],
            # "last_prices_timestamp": int(params["last_prices_timestamp"]),
            "admin_fee": int(params["admin_fee"]),
            "xcp_profit": int(params["xcp_profit"]),
            "xcp_profit_a": int(params["xcp_profit_a"]),
            "timestamp": int(params["timestamp"]),
        }


def _process_reserves(reserves):
    return {
        "normalized": [int(r) for r in reserves["normalizedReserves"]],
        "unnormalized": [int(r) for r in reserves["reserves"]],
        "virtual_price": int(reserves["virtualPrice"]),
        "timestamp": int(reserves["timestamp"]),
    }
