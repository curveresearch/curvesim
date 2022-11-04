from .sources import coingecko, local, nomics


def get(coins, days=60, data_dir="data", src="coingecko"):
    if src == "coingecko":
        prices, volumes, pzero = coingecko(coins, days=days)

    elif src == "nomics":
        prices, volumes, pzero = nomics(coins, days=days, data_dir=data_dir)

    elif src == "local":
        prices, volumes, pzero = local(coins, data_dir=data_dir)

    return prices, volumes, pzero
