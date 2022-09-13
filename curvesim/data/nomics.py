import os
from datetime import timedelta, timezone
from itertools import combinations
from time import sleep

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()
key = os.environ.get("NOMICS_API_KEY")


def get_mkt(market, t_start, t_end):
    # Round times to nearest 30-min interval (floor)
    t_start = t_start.replace(minute=t_start.minute // 30 * 30, second=0, microsecond=0)
    t_end = t_end.replace(minute=t_end.minute // 30 * 30, second=0, microsecond=0)

    # Divide timerange into 14-day chunks
    t_starts = pd.date_range(start=t_start, end=t_end, freq="14d")
    t_ends = t_starts + timedelta(days=14) - timedelta(minutes=30)

    t_starts = t_starts.to_list()
    t_ends = t_ends.to_list()
    t_ends[-1] = t_end  # replace last value with end of total timerange

    # Request parameters
    url = "https://api.nomics.com/v1/exchange_candles"
    p = {"key": key, "interval": "30m", "exchange": market[0], "market": market[1]}

    # Requests
    data = []  # list of dataframes we concat at the end
    for i in range(len(t_starts)):
        p["start"] = t_starts[i].strftime("%Y-%m-%dT%H:%M:%SZ")
        p["end"] = t_ends[i].strftime("%Y-%m-%dT%H:%M:%SZ")

        getData = True
        while getData:
            r = requests.get(url, params=p)
            if r.status_code == 200:
                getData = False
            else:
                print(str(r.status_code))
                sleep(0.1)
        if r.json():
            data.append(pd.DataFrame(r.json())[["timestamp", "close", "volume"]].set_index("timestamp"))

    # Combine & Format data
    if data:
        data = pd.concat(data)
        data.columns = ["price", "volume"]
    else:
        data = pd.DataFrame(columns=["price", "volume"])
    data.index = pd.to_datetime(data.index)
    data["price"] = pd.to_numeric(data["price"]) ** market[2]  # take reciprocal when base/quote reversed
    if market[2] == 1:
        data["volume"] = pd.to_numeric(data["volume"])
    elif market[2] == -1:
        data["volume"] = pd.to_numeric(data["volume"]) / data["price"]

    # Fill in missing data with zeros
    t_samples = pd.date_range(start=t_start, end=t_end, freq="30min", tz=timezone.utc)
    data = data.reindex(t_samples, fill_value=0)

    return data


def get_agg(coins, t_start, t_end, exp=1):
    # Round times to nearest 5-min interval (floor)
    t_start = t_start.replace(minute=t_start.minute // 30 * 30, second=0, microsecond=0)
    t_end = t_end.replace(minute=t_end.minute // 30 * 30, second=0, microsecond=0)

    # Divide timerange into 3-day chunks
    t_starts = pd.date_range(start=t_start, end=t_end, freq="14d")
    t_ends = t_starts + timedelta(days=14) - timedelta(minutes=30)

    t_starts = t_starts.to_list()
    t_ends = t_ends.to_list()
    t_ends[-1] = t_end  # replace last value with end of total timerange

    # Request parameters
    url = "https://api.nomics.com/v1/markets/candles"
    p = {"key": key, "interval": "30m", "base": coins[0], "quote": coins[1]}

    # Requests
    data = []  # list of dataframes we concat at the end
    for i in range(len(t_starts)):
        p["start"] = t_starts[i].strftime("%Y-%m-%dT%H:%M:%SZ")
        p["end"] = t_ends[i].strftime("%Y-%m-%dT%H:%M:%SZ")

        getData = True
        while getData:
            r = requests.get(url, params=p)
            if r.status_code == 200:
                getData = False
            else:
                print(str(r.status_code))
                sleep(0.1)
        if r.json():
            data.append(pd.DataFrame(r.json())[["timestamp", "close", "volume"]].set_index("timestamp"))

    # Combine & Format data
    if data:
        data = pd.concat(data)
        data.columns = ["price", "volume"]
    else:
        data = pd.DataFrame(columns=["price", "volume"])

    data.index = pd.to_datetime(data.index)
    data["price"] = pd.to_numeric(data["price"]) ** exp  # take reciprocal when base/quote reversed
    if exp == 1:
        data["volume"] = pd.to_numeric(data["volume"])
    elif exp == -1:
        data["volume"] = pd.to_numeric(data["volume"]) / data["price"]

    # Fill in missing data with zeros
    t_samples = pd.date_range(start=t_start, end=t_end, freq="30min", tz=timezone.utc)
    data = data.reindex(t_samples, fill_value=0)

    return data


def vwap_mkt(markets, t_start, t_end):
    prices = []
    volumes = []
    for market in markets:
        data = get_mkt(market, t_start, t_end)
        prices.append(data["price"])
        volumes.append(data["volume"])

    prices = pd.concat(prices, axis=1)
    volumes = pd.concat(volumes, axis=1)

    sum_volume = volumes.sum(1)
    weights = volumes.divide(sum_volume, "index")
    vwap = (prices * weights.values).sum(1)

    data = pd.concat([vwap, sum_volume], axis=1)
    data.columns = ["price", "volume"]

    return data


def vwap_agg(coins, t_start, t_end):
    prices = []
    volumes = []

    # Using input base/quote
    data = get_agg(coins, t_start, t_end, exp=1)
    prices.append(data["price"])
    volumes.append(data["volume"])

    # Using reversed base-quote
    data = get_agg([coins[1], coins[0]], t_start, t_end, exp=-1)
    prices.append(data["price"])
    volumes.append(data["volume"] / data["price"])

    prices = pd.concat(prices, axis=1)
    volumes = pd.concat(volumes, axis=1)

    sum_volume = volumes.sum(1)
    weights = volumes.divide(sum_volume, "index")
    vwap = (prices * weights.values).sum(1)

    data = pd.concat([vwap, sum_volume], axis=1)
    data.columns = ["price", "volume"]

    return data


def update(coins, quote, t_start, t_end, pairs=False):  # noqa: C901
    t_start = t_start.replace(tzinfo=timezone.utc)
    t_start_orig = t_start
    t_end = t_end.replace(tzinfo=timezone.utc)

    # If no quote, get prices for each pair of coins
    if quote is None:
        if pairs is False:
            combos = list(combinations(coins, 2))
        else:
            combos = coins

        for pair in combos:
            print("Downloading " + pair[0] + "-" + pair[1])
            try:
                curr_file = pd.read_csv("data/" + pair[0] + "-" + pair[1] + ".csv", index_col=0)
                curr_file.index = pd.to_datetime(curr_file.index)

                if t_start_orig < curr_file.index[-1]:
                    t_start = pd.to_datetime(curr_file.index[-1]) + timedelta(minutes=30)
                    t_start = t_start.replace(tzinfo=timezone.utc)
                else:
                    t_start = t_start_orig

                if t_start < t_end:
                    data = vwap_agg(pair, t_start, t_end)
                    data = curr_file.append(data)
                    data = data[data.index >= t_start_orig]
                    data.to_csv("data/" + pair[0] + "-" + pair[1] + ".csv")
            except Exception:
                data = vwap_agg(pair, t_start_orig, t_end)
                data.to_csv("data/" + pair[0] + "-" + pair[1] + ".csv")

    # If quote given, get prices for each coin in quote currency
    else:
        for coin in coins:
            curr_coins = [coin, quote]
            try:
                curr_file = pd.read_csv("data/" + coin + "-" + quote + ".csv", index_col=0)
                curr_file.index = pd.to_datetime(curr_file.index)

                if t_start_orig < curr_file.index[-1]:
                    t_start = pd.to_datetime(curr_file.index[-1]) + timedelta(minutes=30)
                    t_start = t_start.replace(tzinfo=timezone.utc)
                else:
                    t_start = t_start_orig

                if t_start < t_end:
                    data = vwap_agg(curr_coins, t_start, t_end)
                    data = curr_file.append(data)
                    data = data[data.index >= t_start_orig]
                    data.to_csv("data/" + coin + "-" + quote + ".csv")
            except Exception:
                data = vwap_agg(curr_coins, t_start_orig, t_end)
                data.to_csv("data/" + coin + "-" + quote + ".csv")


def poolprices(  # noqa: C901
    coins=[], quote=None, quotediv=False, t_start=None, t_end=None, resample=None, pairs=[], data_dir="data"
):
    """
    Loads and formats price/volume data from CSVs.

    coins: list of coins to load (e.g., ['DAI', 'USDC', 'USDT'])
    quote: if string, name of quote currency to load (e.g., 'USD')
    quotediv: determine pairwise coin prices using third currency (e.g., ETH-SUSD/SETH-SUSD for ETH-SETH)
    t_start/t_end: used to truncate input time series
    resample: used to downsample input time series
    pairs: list of coin pairs to load (e.g., ['DAI-USDC', 'USDC-USDT'])
    data_dir: base directory name for price csv files

    Returns exchange rates/volumes for each coin pair in order of list(itertools.combinations(coins,2))

    """
    if pairs and coins:
        raise ValueError("Use only 'coins' or 'pairs', not both.")

    if coins:
        if quote:
            symbol_pairs = zip(coins, [quote] * len(coins))
        else:
            symbol_pairs = list(combinations(coins, 2))
    elif pairs:
        symbol_pairs = pairs
    else:
        raise ValueError("Must use one of 'coins' or 'pairs'.")

    prices = []
    volumes = []
    for (sym_1, sym_2) in symbol_pairs:
        filename = os.path.join(data_dir, f"{sym_1}-{sym_2}.csv")
        data_df = pd.read_csv(filename, index_col=0)
        prices.append(data_df["price"])
        volumes.append(data_df["volume"])

    prices = pd.concat(prices, axis=1)
    volumes = pd.concat(volumes, axis=1)

    pzero = (prices == 0).mean()

    prices = prices.replace(to_replace=0, method="ffill")  # replace price=0 with previous price
    prices = prices.replace(
        to_replace=0, method="bfill"
    )  # replace any price=0 at beginning with subsequent price

    # If quotediv, calc prices for each coin pair from prices in quote currency
    if quotediv:
        combos = list(combinations(range(len(coins)), 2))
        prices_tmp = []
        volumes_tmp = []

        for pair in combos:
            prices_tmp.append(prices.iloc[:, pair[0]] / prices.iloc[:, pair[1]])  # divide prices
            volumes_tmp.append(volumes.iloc[:, pair[0]] + volumes.iloc[:, pair[1]])  # sum volumes

        prices = pd.concat(prices_tmp, axis=1)
        volumes = pd.concat(volumes_tmp, axis=1)

    # Index as date-time type
    prices.index = pd.to_datetime(prices.index)
    volumes.index = pd.to_datetime(volumes.index)

    # Trim to t_start and/or t_end
    if t_start is not None:
        prices = prices.loc[t_start:]
        volumes = volumes.loc[t_start:]

    if t_end is not None:
        prices = prices.loc[:t_end]
        volumes = prices.loc[:t_end]

    # Resample times
    if resample is not None:
        prices = prices.resample(resample).first()
        volumes = volumes.resample(resample).sum()
    else:
        prices.index.freq = pd.infer_freq(prices.index)
        volumes.index.freq = pd.infer_freq(volumes.index)

    return prices, volumes, pzero
