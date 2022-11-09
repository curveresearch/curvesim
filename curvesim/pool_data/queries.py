import asyncio

from ..network.coingecko import crosschain_coin_addresses_sync
from ..network.subgraph import pool_snapshot_sync, symbol_address_sync
from ..network.web3 import underlying_coin_addresses_sync


def from_address(address, chain):
    loop = asyncio.get_event_loop()
    data = pool_snapshot_sync(address, chain, event_loop=loop)

    # Get mainnet addresses for coins
    m_addrs = crosschain_coin_addresses_sync(
        data["coins"]["addresses"], chain, "mainnet", event_loop=loop
    )

    data["coins"]["addresses"] = m_addrs

    # Get underlying token addresses
    if data["pool_type"] == "LENDING":
        u_addrs = underlying_coin_addresses_sync(m_addrs, event_loop=loop)

        m = data.pop("coins")
        names = [n[1:] for n in m["names"]]

        data["coins"] = {"names": names, "addresses": u_addrs, "wrapper": m}

    return data


def from_symbol(symbol, chain, balanced=(True, True)):
    address = symbol_address_sync(symbol, chain)

    data = from_address(address, chain)

    return data
