from ast import literal_eval

import numpy as np
import pandas as pd
import requests
from web3 import Web3

from .pool import pool


def getpool(poolname, D=None, src="cg", balanced=False):
    # Get current pool data
    print("[" + poolname + "] Fetching pool data...")
    if src == "cg":
        csv = "poolDF_cg.csv"
    else:
        csv = "poolDF_nomics.csv"

    pldata = pooldata(poolname, csv=csv, balanced=balanced)

    # Over-ride D if necessary
    if D is None:
        D = pldata["D"]
    else:
        D = int(D * 10**18)
        if isinstance(pldata["D"], list):  # if metapool
            pldata["D"][0] = D
            D = pldata["D"]

    if pldata["A_base"] is not None:
        A = [pldata["A"], pldata["A_base"]]
    else:
        A = pldata["A"]

    if pldata["fee_base"] is not None:
        fee = [pldata["fee"], pldata["fee_base"]]
    else:
        fee = pldata["fee"]

    if pldata["r"] is not None:
        r = int(pldata["r"].price[-1])
    else:
        r = None

    pl = pool(A, D, pldata["n"], fee=fee, tokens=pldata["tokens"], feemul=pldata["feemul"], r=r)
    pl.histvolume = pldata["histvolume"]
    pl.coins = pldata["coins"]

    return pl


def pooldata(poolname, csv="poolDF_cg.csv", balanced=False):  # noqa: C901
    w3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/aae0ec63797d4548bfe5c98c4f9aa230"))

    pools = pd.read_csv(
        csv,
        sep=";",
        header=0,
        index_col=0,
        converters={
            "coins": literal_eval,
            "precmul": literal_eval,
            "tokentype": literal_eval,
        },
    )
    p = pools.loc[poolname]

    ABItypes = ["uint256", "int128"]  # some old contracts used int128
    for ABItype in ABItypes:
        abi = (
            '[{"name":"A","outputs":[{"type":"uint256","name":""}],"inputs":[],"stateMutability":"view","type":"function","gas":5227},{"name":"balances","outputs":[{"type":"uint256","name":""}],"inputs":[{"type":"'  # noqa: E501
            + ABItype
            + '","name":"arg0"}],"stateMutability":"view","type":"function","gas":2250},{"name":"fee","outputs":[{"type":"uint256","name":""}],"inputs":[],"stateMutability":"view","type":"function","gas":2171},{"name":"get_virtual_price","outputs":[{"type":"uint256","name":""}],"inputs":[],"stateMutability":"view","type":"function","gas":1133537},{"name":"coins","outputs":[{"type":"address","name":""}],"inputs":[{"type":"'  # noqa: E501
            + ABItype
            + '","name":"arg0"}],"stateMutability":"view","type":"function","gas":2310}]'
        )
        contract = w3.eth.contract(address=p.address, abi=abi)
        try:
            contract.functions.balances(0).call()
            break
        except Exception:
            pass

    coins = p.coins

    if p.feemul == "None":
        feemul = None
    else:
        feemul = int(p.feemul)

    if p.precmul[0] == "r":
        # load redemption price data as r
        # update precmul based on redemption price
        r = redemptionprices(1000)
        p.precmul = [r.price[-1] / 10**18]
    else:
        r = None

    A = contract.functions.A().call()
    fee = contract.functions.fee().call()

    if p.basepool == "None":  # normal pool

        D = []
        for i in range(len(p.coins)):
            if p.tokentype:  # if any assets are ctokens/ytokens
                if p.tokentype[i]:  # if asset[i] is ctoken/ytoken
                    cAddress = contract.functions.coins(i).call()
                    rate = tokenrate(p.tokentype[i], cAddress)
                else:
                    rate = 10**18
            else:
                rate = 10**18

            D.append(contract.functions.balances(i).call() * p.precmul[i] * rate // 10**18)

        n = len(coins)
        A_base = None
        fee_base = None
        addresses = [p.address.lower()]

        pl = pool(A, D, n)
        D_balanced = pl.D()
        tokens = D_balanced * 10**18 // contract.functions.get_virtual_price().call()

        if balanced:
            D = D_balanced

    else:  # meta-pool
        basepool = pools.loc[p.basepool]

        for ABItype in ABItypes:
            abi = (
                '[{"name":"A","outputs":[{"type":"uint256","name":""}],"inputs":[],"stateMutability":"view","type":"function","gas":5227},{"name":"balances","outputs":[{"type":"uint256","name":""}],"inputs":[{"type":"'  # noqa: E501
                + ABItype
                + '","name":"arg0"}],"stateMutability":"view","type":"function","gas":2250},{"name":"fee","outputs":[{"type":"uint256","name":""}],"inputs":[],"stateMutability":"view","type":"function","gas":2171},{"name":"get_virtual_price","outputs":[{"type":"uint256","name":""}],"inputs":[],"stateMutability":"view","type":"function","gas":1133537},{"name":"coins","outputs":[{"type":"address","name":""}],"inputs":[{"type":"'  # noqa: E501
                + ABItype
                + '","name":"arg0"}],"stateMutability":"view","type":"function","gas":2310}]'
            )
            base_contract = w3.eth.contract(address=basepool.address, abi=abi)
            try:
                base_contract.functions.balances(0).call()
                break
            except Exception:
                pass

        D = []
        precmul = p.precmul
        precmul.append(base_contract.functions.get_virtual_price().call() / 10**18)
        for i in range(len(p.coins) + 1):
            D.append(int(contract.functions.balances(i).call() * precmul[i]))

        D_base = []
        for i in range(len(basepool.coins)):
            D_base.append(int(base_contract.functions.balances(i).call() * basepool.precmul[i]))

        D = [D, D_base]
        n = [len(p.coins) + 1, len(basepool.coins)]
        coins.extend(basepool.coins)
        A_base = base_contract.functions.A().call()
        fee_base = base_contract.functions.fee().call()
        addresses = [p.address.lower(), basepool.address.lower()]

        pl = pool([A, A_base], D, n)
        D_base_balanced = pl.basepool.D()
        tokens = D_base_balanced * 10**18 // base_contract.functions.get_virtual_price().call()

        if balanced:
            pl = pool([A, A_base], D, n, tokens=tokens)
            rates = pl.p[:]
            rates[pl.max_coin] = pl.basepool.get_virtual_price()
            if r is not None:
                rates[pl.max_coin - 1] = int(r.price[-1])
            xp = [x * p // 10**18 for x, p in zip(pl.x, rates)]
            D_balanced = pl.D(xp=xp)
            D = [D_balanced, D_base_balanced]

    # Get historical volume
    url = "https://api.thegraph.com/subgraphs/name/convex-community/volume-mainnet"

    histvolume = []
    for address in addresses:
        query = (
            """{
  swapVolumeSnapshots(
    where: {pool: "%s", period: 86400},
    orderBy: timestamp,
    orderDirection: desc,
    first:60
  ) {
    volume
  }
}"""
            % address
        )
        req = requests.post(url, json={"query": query})
        try:
            volume = pd.DataFrame(req.json()["data"]["swapVolumeSnapshots"], dtype="float").sum()[0]
        except Exception:
            print("[" + poolname + "] No historical volume info from Curve Subgraph.")
            volume = float(input("[" + poolname + "] Please input estimated volume for 2 months: "))
        histvolume.append(volume)

    histvolume = np.array(histvolume)

    # Format output as dict
    data = {
        "D": D,
        "coins": coins,
        "n": n,
        "A": A,
        "A_base": A_base,
        "fee": fee,
        "fee_base": fee_base,
        "tokens": tokens,
        "feemul": feemul,
        "histvolume": histvolume,
        "r": r,
    }

    return data


def tokenrate(tokentype, address):
    w3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/aae0ec63797d4548bfe5c98c4f9aa230"))

    if tokentype == "c":
        abi = '[{"constant":true,"inputs":[],"name":"exchangeRateStored","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"}]'  # noqa: E501
        contract = w3.eth.contract(address=address, abi=abi)
        rate = contract.functions.exchangeRateStored().call()

    elif tokentype == "y":
        abi = '[{"constant":true,"inputs":[],"name":"getPricePerFullShare","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"}]'  # noqa: E501
        contract = w3.eth.contract(address=address, abi=abi)
        rate = contract.functions.getPricePerFullShare().call()

    return rate


def redemptionprices(n=100):
    url = "https://api.thegraph.com/subgraphs/name/reflexer-labs/rai-mainnet"
    query = (
        """
{
  redemptionPrices(orderBy: timestamp, orderDirection: desc, first: %d) {
    timestamp
    value
  }
}"""
        % n
    )

    r = requests.post(url, json={"query": query})
    data = pd.DataFrame(r.json()["data"]["redemptionPrices"])
    data.columns = ["timestamp", "price"]
    data.price = (data.price.astype(float) * 10**18).astype(int)
    data.timestamp = pd.to_datetime(data.timestamp, unit="s", utc=True)
    data.sort_values("timestamp", inplace=True)
    data.set_index("timestamp", inplace=True)

    return data
