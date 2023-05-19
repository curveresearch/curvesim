from pandas import concat

from curvesim.plot.altair import result_plotter as altair_plotter


class SimResults:
    """
    Results container with methods to plot or return metrics as DataFrames.
    """

    __slots__ = [
        "data_per_run",
        "data_per_trade",
        "summary_data",
        "factors",
        "plot_config",
        "plotter",
    ]

    def __init__(
        self,
        data_per_run,
        data_per_trade,
        summary_data,
        factors,
        plot_config,
        plotter=altair_plotter,
    ):
        self.data_per_run = data_per_run
        self.data_per_trade = data_per_trade
        self.summary_data = summary_data

        self.factors = factors
        self.plot_config = plot_config
        self.plotter = plotter

    def summary(self, full=False, columns=None):
        """
        Returns a DataFrame of summary metrics.

        Parameters
        ----------
        full : bool, default=False
            If true, includes per-run data (e.g., pool parameters) in the output.

        columns: list, optional
            The metrics to include in the output DataFrame. Top level metric names
            (e.g., "pool_balance") should be used without specifying the individual
            summary statistics (e.g., not "pool_balance min").

            By default, includes all metrics.

        Returns
        -------
        pandas.DataFrame
            A DataFrame with metrics as columns and each simulation run as rows.

        """
        data = get_columns(self.summary_data, columns)

        if full or columns:
            runs = get_columns(self.data_per_run, columns)
            cols = [" ".join(c) for c in data.columns.values]  # flatten multi-index
            data = data.set_axis(cols, axis=1)
            return concat([runs, data], axis=1)

        return data

    def data(self, full=False, columns=None):
        """
        Returns a DataFrame of metrics for each time-point in the simulation.

        Parameters
        ----------
        full : bool, default=False
            If true, includes per-run data (e.g., pool parameters) in the output.

        columns: list, optional
            The metrics to include in the output DataFrame.
            By default, includes all metrics.

        Returns
        -------
        pandas.DataFrame
            A DataFrame with metrics as columns and each timestamp in each run as rows.

        """
        data = get_columns(self.data_per_trade, columns, defaults=["run", "timestamp"])

        if full or columns:
            runs = get_columns(self.data_per_run, columns)
            runs = runs.loc[data["run"]].reset_index(drop=True)  # include run data
            return concat([runs, data], axis=1)

        return data

    def plot(self, summary=True, data=True, save_as=None):
        """
        Returns and optionally saves a plot of the results data.

        Parameters
        ----------
        summary : bool, default=True
            If true, includes summary data in the plot.

        data : bool, default=True
            If true, includes timeseries data in the plot.

        save_as : str, optional
            Path to save plot output to. Typically an .html file. See
            `Altair docs <https://altair-viz.github.io/user_guide/saving_charts.html>`_
            for additional options.


        Returns
        -------
        altair.VConcatChart

        """
        return self.plotter.plot(self, summary, data, save_as)


def get_columns(data, columns, defaults=None):
    """Returns specified DataFrame columns if present. If none, returns all columns."""

    if not columns:
        return data
    if defaults:
        columns = defaults + columns
    columns = [c for c in columns if c in data.columns]
    return data[columns]
