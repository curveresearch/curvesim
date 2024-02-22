"""
DataSources for local files and helper functions.
"""

from pandas import MultiIndex, read_csv

from curvesim.logging import get_logger
from curvesim.templates import FileDataSource

logger = get_logger(__name__)


class CsvDataSource(FileDataSource):
    """
    DataSource for local price/volume data stored in CSV files.
    """

    @property
    def file_extension(self):
        return "csv"

    def _default_read_function(self, filepath, sim_asset, time_sequence):
        symbol_pair = (sim_asset.base.symbol, sim_asset.quote.symbol)
        df = read_csv(filepath, index_col=0, parse_dates=True)

        if len(df.index) != len(time_sequence) or any(df.index != time_sequence):
            df = _reindex_to_time_sequence(df, time_sequence, symbol_pair)

        columns = [(col, symbol_pair) for col in df.columns]
        df.columns = MultiIndex.from_tuples(columns, names=["metric", "symbol"])

        return df


def _reindex_to_time_sequence(df, time_sequence, asset_id):
    df_reindexed = df.reindex(time_sequence, method="ffill", limit=1)
    nan_count = df_reindexed.isna().sum()

    logger.info(
        (
            "\nResampling %s...\n"
            "Average data frequency: %s\n"
            "Resampling to: %s\n"
            "Filling NaN values:\n%s"
        ),
        asset_id,
        df.index.to_series().diff().mean(),
        time_sequence.freq,
        nan_count.to_string(),
    )

    if any(nan_count > 0):
        df_reindexed["price"] = df_reindexed["price"].ffill()
        df_reindexed["volume"] = df_reindexed["volume"].fillna(0)

    return df_reindexed
