"""
Coingecko price/volume Data Source and helper functions.
"""

from datetime import datetime

from pandas import DataFrame, concat

from curvesim.exceptions import DataSourceError
from curvesim.logging import get_logger
from curvesim.network.coingecko import coin_id_from_address_sync, get_prices_sync
from curvesim.templates import (
    ApiDataSource,
    DateTimeSequence,
    OnChainAssetPair,
    OnChainAsset,
    TimeSequence,
)
from curvesim.utils import cache, get_event_loop

logger = get_logger(__name__)


class CoinGeckoPriceVolumeSource(ApiDataSource):
    """
    DataSource for Coingecko price/volume data.
    """

    def query(self, sim_asset: OnChainAssetPair, time_sequence: TimeSequence[datetime]) -> DataFrame:
        """
        Fetches asset data for a particular range of times. Timestamps are matched with
        a tolerance of 10 minutes, then missing prices are frontfilled and missing
        volume is filled with zeros.

        Parameters
        ----------
        sim_asset: OnChainAssetPair
            The asset-pair to pull data for.

        time_sequence: TimeSequence
            Timestamps to pull data for.

        Returns
        -------
        pandas.DataFrame
        """

        # # test
        # new_sim_assets = []
        # for asset in sim_asset:
        #     id = asset.id if asset.id != "0xeeee" else "ETH"
        #     address = (
        #         asset.address
        #         if asset.address != "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
        #         else "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
        #     )
        #     asset = OnChainAsset(id, id, address, asset.chain)
        #     new_sim_assets.append(asset)

        # new_sim_assets = OnChainAssetPair(new_sim_assets[0], new_sim_assets[1])
        # sim_asset = new_sim_assets
        # # test

        symbol_pair = (sim_asset.base.symbol, sim_asset.quote.symbol)

        logger.info("Fetching CoinGecko price data for %s...", "-".join(symbol_pair))

        _validate_arguments(sim_asset, time_sequence)
        t_start, t_end = _get_time_endpoints(time_sequence)

        data = []
        for asset in sim_asset:
            coingecko_id = self._get_coingecko_id(asset.address, asset.chain)
            _data = self._get_usd_price(coingecko_id, t_start, t_end)
            _data = _reindex_to_time_sequence(_data, time_sequence, asset.id)
            data.append(_data)

        # divide prices: (usd/base) / (usd/quote) = quote/base
        # sum volumes and convert to base: usd / (usd/base) = base
        base_data, quote_data = data
        prices = base_data["price"] / quote_data["price"]
        volumes = (base_data["volume"] + quote_data["volume"]) / base_data["price"]

        df = concat(
            [prices, volumes],
            axis=1,
            keys=[("price", symbol_pair), ("volume", symbol_pair)],
            names=["metric", "symbol"],
        )

        return df

    @staticmethod
    @cache
    def _get_coingecko_id(address, chain):
        loop = get_event_loop()
        return coin_id_from_address_sync(address, chain, event_loop=loop)

    @staticmethod
    @cache
    def _get_usd_price(coingecko_id, t_start, t_end):
        loop = get_event_loop()
        return get_prices_sync(coingecko_id, "USD", t_start, t_end, event_loop=loop)


def _validate_arguments(sim_asset, time_sequence):
    if not isinstance(sim_asset, OnChainAssetPair):
        _type = type(sim_asset).__name__
        raise DataSourceError(f"For CoinGecko, sim_asset must be 'OnChainAssetPair', not '{_type}'.")

    if not isinstance(time_sequence, DateTimeSequence):
        _type = type(time_sequence).__name__
        raise DataSourceError(f"For CoinGecko, time_sequence must be 'DateTimeSequence', not '{_type}'.")


def _get_time_endpoints(time_sequence, buffer=3600):
    t_start = time_sequence[0].timestamp() - buffer
    t_end = time_sequence[-1].timestamp() + buffer
    return t_start, t_end


def _reindex_to_time_sequence(df, time_sequence, asset_id):
    # Use "nearest" because CoinGecko timestamps are usually slightly delayed
    df_reindexed = df.reindex(time_sequence, method="nearest", tolerance="10min")
    nan_count = df_reindexed.isna().sum()

    logger.info(
        ("\nResampling '%s'...\n" "Average data frequency: %s\n" "Resampling to: %s\n" "Filling NaN values:\n%s"),
        asset_id,
        df.index.to_series().diff().mean(),
        time_sequence.freq,
        nan_count.to_string(),
    )

    if any(nan_count > 0):
        df_reindexed["price"] = df_reindexed["price"].ffill()
        df_reindexed["volume"] = df_reindexed["volume"].fillna(0)

    return df_reindexed
