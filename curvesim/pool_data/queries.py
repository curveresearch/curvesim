import asyncio

from ..network.coingecko import crosschain_coin_addresses
from ..network.subgraph import redemption_price, snapshot, symbol_address
from ..network.web3 import underlying_coin_addresses


def from_address(address, chain, balanced=(True, True), days=60):
    loop = asyncio.get_event_loop()
    tasks = [snapshot(address, chain), redemption_price(address=address, chain=chain)]

    data, r = loop.run_until_complete(asyncio.gather(*tasks))

    # Add redemption price data
    data.update({"r": r})

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


def from_symbol(symbol, chain, balanced=(True, True), days=60):
    loop = asyncio.get_event_loop()

    address = loop.run_until_complete(symbol_address(symbol, chain))

    data = from_address(address, chain, balanced=balanced, days=days)

    return data
