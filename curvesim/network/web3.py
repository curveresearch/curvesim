"""
Network connector for on-chain data
"""

from asyncio import gather, sleep

from web3 import AsyncHTTPProvider, Web3
from web3.eth import AsyncEth

from curvesim.utils import get_env_var

from .http import HTTP
from .utils import sync

ETHERSCAN_URL = "https://api.etherscan.io/api"


def get_etherscan_api_key():
    """
    Get the Etherscan API key from the environment.
    Default to key provided by `curvesim` (not recommended).
    """
    default_key = "PT1D9IGAPPPRFMD312V9GARWW93BS9ZV6V"
    key = get_env_var("ETHERSCAN_API_KEY", default=default_key)
    return key


def get_alchemy_api_key():
    """
    Get the Alchemy API key from the environment.
    Default to key provided by `curvesim` (not recommended).
    """
    default_key = "WLcYLj9I1w7wEOgKmzidN1z62sbFILUz"
    key = get_env_var("ALCHEMY_API_KEY", default=default_key)
    return key


async def explorer(params):
    """
    Async function to retrieve data from the chain explorer (Etherscan).

    Parameters
    ----------
    params : dict
        Must include keys for module, action, and any required arguments for the query.

    Returns
    -------
    dict
        Query result

    """
    etherscan_api_key = get_etherscan_api_key()
    params.update({"apikey": etherscan_api_key})

    t_wait = 0.2
    while True:
        r = await HTTP.get(ETHERSCAN_URL, params=params)
        result = r["result"]

        if result.startswith("Max rate limit reached"):
            await sleep(t_wait)
            t_wait = round(t_wait * 1.5, 2)
        else:
            break

    return result


async def ABI(address):
    """
    Async function to retrieves ABI from the chain explorer (Etherscan).

    Parameters
    ----------
    address : str
        Address for the contract on Ethereum mainnet.

    Returns
    -------
    abi : str

    """
    p = {
        "module": "contract",
        "action": "getabi",
        "address": address,
    }

    abi = await explorer(p)

    return abi


_web3 = None


def _load_web3():
    alchemy_api_key = get_alchemy_api_key()
    global _web3  # pylint: disable=global-statement
    if not _web3:
        _web3 = Web3(
            AsyncHTTPProvider(
                f"https://eth-mainnet.g.alchemy.com/v2/{alchemy_api_key}",
                request_kwargs={"headers": {"Accept-Encoding": "gzip"}},
            ),
            modules={"eth": (AsyncEth,)},
            middlewares=[],
        )
    return _web3


async def contract(address, abi=None):
    """
    Creates an async Web3py contract object.

    Parameters
    ----------
    address : str
        Address for the contract on Ethereum mainnet.

    Returns
    -------
    contract : web3.contract.AsyncContract

    """
    abi = abi or await ABI(address)
    w3 = _load_web3()
    c = w3.eth.contract(address=address, abi=abi)
    return c


async def _underlying_coin_address(address):
    c = await contract(address)

    fns = ["upgradeToAndCall", "underlying", "token"]
    n_fns = len(fns) - 1

    for i, fn in enumerate(fns):
        if fn in dir(c.functions):
            break

        if i == n_fns:
            raise ValueError(f"Could not find underlying token for {address}")

    # Handle Aave proxy
    if fn == "upgradeToAndCall":
        abi = await ABI("0x1C050bCa8BAbe53Ef769d0d2e411f556e1a27E7B")
        c = await contract(address, abi)
        fn = "UNDERLYING_ASSET_ADDRESS"

    address = await c.functions[fn]().call()

    return address


async def underlying_coin_addresses(addresses):
    """
    Async function to get the underlying coin addresses for lending tokens
    (aTokens, cTokens, and yTokens).

    Parameters
    ----------
    addresses : iterable of str
        Addresses for the lending tokens on Ethereum mainnet.

    Returns
    -------
    addresses : list of str
        The addresses of the underlying tokens.

    """
    if isinstance(addresses, str):
        addrs = await _underlying_coin_address(addresses)

    else:
        tasks = []
        for address in addresses:
            tasks.append(_underlying_coin_address(address))

        addrs = await gather(*tasks)

    return addrs


# Sync
explorer_sync = sync(explorer)
ABI_sync = sync(ABI)
contract_sync = sync(contract)
underlying_coin_addresses_sync = sync(underlying_coin_addresses)
