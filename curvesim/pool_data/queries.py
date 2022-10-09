import asyncio

from ..network.coingecko import crosschain_coin_addresses
from ..network.subgraph import redemption_prices as _redemption_prices
from ..network.subgraph import snapshot, symbol_address
from ..network.subgraph import volume as _volume
from ..network.web3 import underlying_coin_addresses


def from_address(address, chain, balanced=(True, True)):
    loop = asyncio.get_event_loop()

    data = loop.run_until_complete(snapshot(address, chain))

    # Get mainnet addresses for coins
    addrs = data["coins"]["addresses"]
    m_addrs = loop.run_until_complete(
        crosschain_coin_addresses(addrs, chain, "mainnet")
    )
    data["coins"]["addresses"] = m_addrs

    # Get underlying token addresses
    if data["pool_type"] == "LENDING":
        u_addrs = loop.run_until_complete(underlying_coin_addresses(m_addrs))

        m = data.pop("coins")
        names = [n[1:] for n in m["names"]]

        data["coins"] = {"names": names, "addresses": u_addrs, "wrapper": m}

    return data


def from_symbol(symbol, chain, balanced=(True, True)):
    loop = asyncio.get_event_loop()

    address = loop.run_until_complete(symbol_address(symbol, chain))

    data = from_address(address, chain, balanced=balanced)

    return data


def redemption_prices(address, chain, n=1000):
    loop = asyncio.get_event_loop()
    r = loop.run_until_complete(_redemption_prices(address=address, chain=chain, n=n))

    return r


def volume(address, chain, bp_address=None, days=60):
    loop = asyncio.get_event_loop()

    tasks = [_volume(address, chain, days=days)]
    if bp_address:
        tasks.append(_volume(bp_address, chain, days=days))

    vol = loop.run_until_complete(asyncio.gather(*tasks))

    return vol
