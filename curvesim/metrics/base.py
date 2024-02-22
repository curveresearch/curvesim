"""Base and generic metric classes."""

__all__ = [
    "Metric",
    "PoolMetric",
    "PricingMetric",
    "PoolPricingMetric",
]


from abc import ABC, abstractmethod
from collections.abc import Iterable

from pandas import DataFrame, MultiIndex, Series

from curvesim.exceptions import MetricError
from curvesim.utils import cache, override


class MetricBase(ABC):
    """
    Metric base class with required properties for any metric object in Curvesim.

    Typically, the :func:`compute_metric` method is defined in generalized sub-classes
    (e.g., :class:`Metric`, :class:`PoolMetric`), and the :func:`config` property is
    defined individually for metrics specified in :mod:`.metrics.metrics`.
    """

    def __init__(self, **kwargs):
        """
        All metric classes must include kwargs in their constructor to ignore
        extra keywords passed by :class:`.StateLog`.
        """

    def compute(self, state_log):
        """
        Computes metrics and summary statistics from the data provided by
        :class:`.StateLog` at the end of each simulation run.

        Generally, this method should be left "as is", with any custom processing
        applied in :func:`metric_function`.

        Parameters
        ----------
        state_log : dict
            State log data returned by func:`.StateLog.get_logs()`

        Returns
        -------
            data : DataFrame
                A pandas DataFrame of the computed metrics.

            summary_data : DataFrame or None
                A pandas Dataframe of the summary data computed using
                :func:`summary_functions`. If :func:`summary_functions` is not
                specified, returns None.
        """
        timestamps = state_log["price_sample"].timestamp
        data = self.metric_function(**state_log).set_index(timestamps)
        return data, summarize_data(data, self.summary_functions)

    @property
    @abstractmethod
    def config(self):
        """
        A dict specifying how to compute, summarize, and/or plot the recorded data.
        See :ref:`metric-configuration` for formatting details.

        Raises :python:`NotImplementedError` if property is not defined.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def metric_function(self):
        """
        Returns a function that computes metrics from the state log data
        (see :func:`.StateLog.get_logs()`) input to :func:`compute`.

        The returned function must include kwargs as an argument to ignore
        extra keywords passed by :func:`.StateLog.get_logs()`.

        Returns
        -------
        function : function
            A function that returns a pandas.DataFrame of metric value(s) to be returned
            by :func:`.compute`. DataFrame column names should correspond to sub-metric
            names specified in :func:"config".

            Raises :python:`NotImplementedError` if property is not defined.
        """
        raise NotImplementedError

    @property
    def plot_config(self):
        """
        Configuration for plotting the metric and/or summary statistics. (Optional)

        Returns
        -------
            dict or None
                Plot specification for each sub-metric and/or summary statistic.
                See :ref:`metric-configuration` for format details. Returns None if
                :python:`self.config["plot"]` is not present.
        """

    @property
    def summary_functions(self):
        """
        Specifies functions for computing summary statistics. (Optional)

        Returns
        -------
        dict or None
            A dict specifying the functions used to summarize each sub-metric.
            See :ref:`metric-configuration` for format details. Returns None if
            :python:`self.config["functions"]["summary"]` not present.
        """


class Metric(MetricBase):
    """
    Metric computed using a single function defined in the `config` property.

    The function for computing the metric should be mapped to
    :python:`config["functions"]["metrics"]`.
    """

    @property
    @override
    @cache
    def metric_function(self):
        """
        Returns a function that computes metrics from the state log data
        (see :func:`.StateLog.get_logs()`) input to :func:`compute`.

        Returns
        -------
        self.config["functions"]["metrics"] : function
            Function returning the value(s) to be stored in :python:`self.records`.
            Raises :python:`MetricError` if function not specified in config.
        """
        try:
            return self.config["functions"]["metrics"]

        except KeyError as e:
            metric_type = self.__class__.__name__
            raise MetricError(
                f"Metric function not found in {metric_type} config.)"
            ) from e

    @property
    @override
    def plot_config(self):
        """
        Configuration for plotting the metric and/or summary statistics. (Optional)

        Returns
        -------
        config["plot"] : dict or None
            Plot specification for each sub-metric and/or summary statistic.
            See :ref:`metric-configuration` for format details. Returns None if
            :python:`self.config["plot"]` is not present.
        """
        try:
            return self.config["plot"]
        except KeyError:
            return None

    @property
    @override
    def summary_functions(self):
        """
        Specifies functions for computing summary statistics. (Optional)

        Returns
        -------
        config["functions"]["summary"] : dict or None
            A dict specifying the functions used to summarize each sub-metric.
            See :ref:`metric-configuration` for format details. Returns None if
            :python:`self.config["functions"]["summary"]` not present.
        """
        try:
            return self.config["functions"]["summary"]
        except KeyError:
            return None


def summarize_data(record_df, summary_functions):
    """
    Helper function to compute summary statistics.
    """
    if not summary_functions:
        return None

    indices = []
    data = []
    for metric, functions in summary_functions.items():
        functions = format_summary_functions(functions)

        for name, fn in functions:
            stat = compute_summary_stat(record_df[metric], fn)
            indices.append((metric, name))
            data.append(stat)

    index = MultiIndex.from_tuples(indices, names=["metric", "stat"])
    return DataFrame([data], columns=index)


def format_summary_functions(functions):
    """
    Returns summary functions as a list of (name, function) tuple pairs.
    """
    if isinstance(functions, str):
        return [(functions, functions)]
    if isinstance(functions, dict):
        return list(functions.items())
    if isinstance(functions, Iterable):
        return [(fn, fn) for fn in functions]

    return functions


def compute_summary_stat(data, fn):
    """
    Computes a summary statistic for "data" using the function "fn". If fn is a str,
    it is interpreted as a pandas.DataFrame method.
    """
    if isinstance(fn, str):
        return getattr(data, fn)()

    return fn(data)


class PoolMetric(Metric):
    """
    :class:`Metric` with distinct configs for different pool-types. Typically
    used when different pool-types require unique functions to compute a metric.

    PoolMetrics must specify a :func:`pool_config` which maps individual pool
    types to dicts in the format of :func:`MetricBase.config`.
    """

    __slots__ = ["_pool"]

    def __init__(self, pool, **kwargs):
        """
        Parameters
        ----------
        pool : SimPool object
            A pool simulation interface. Used to select the pool's configuration from
            :func:`pool_config` and stored as :python:`self._pool` for access during
            metric computations.
        """
        self._pool = pool
        super().__init__(**kwargs)  # kwargs are ignored

    @property
    @abstractmethod
    def pool_config(self):
        """
        A dict mapping pool types to dicts in the format of :func:`MetricBase.config`.
        See :ref:`metric-configuration` for format details.

        Raises :python:`NotImplementedError` if property is not defined.
        """
        raise NotImplementedError

    def set_pool(self, pool):
        self._pool = pool

    def set_pool_state(self, pool_state):
        for attr, val in pool_state.items():
            if attr.endswith("_base"):
                setattr(self._pool.basepool, attr[:-5], val)
            else:
                setattr(self._pool, attr, val)

    @property
    @override
    @cache
    def config(self):
        """
        Returns the config corresponding to the pool's type in :func:`pool_config`.

        Generally, this property should be left "as is", with pool-specific configs
        defined in :func:`pool_config`.
        """
        try:
            return self.pool_config[type(self._pool)]
        except KeyError as e:
            metric_type = self.__class__.__name__
            pool_type = self._pool.__class__.__name__
            raise MetricError(
                f"Pool type {pool_type} not found in {metric_type} pool_config.)"
            ) from e


class PricingMixin:
    """
    Mixin to incorporate current simulation prices into computations.

    Also provides :code:`numeraire` and :code:`numeraire_idx` attributes for computing
    prices or values with a preferred numeraire.
    """

    def __init__(self, coin_names, **kwargs):
        """
        Parameters
        ----------
        coin_names : iterable of str
            Symbols for the coins used in a simulation. A numeraire is selected from
            the specified coins.
        """
        self.numeraire = get_numeraire(coin_names)
        super().__init__(**kwargs)

    def get_market_price(self, base, quote, prices):
        """
        Returns exchange rate for two coins identified by their pool indicies.

        Parameters
        ----------
        base : str
            Symbol for the "in" coin; the "base" currency
        quote : str
            Symbol for the "out" coin; the "quote" currency
        prices : pandas.DataFrame, pandas.Series, or dict
            Market prices for each pair. In the simulator context, this is provided on
            each iteration of the :mod:`price_sampler`.

        Returns
        -------
        float
            The price of the "base" coin, quoted in the "quote" coin.

        """
        coin_pairs = get_coin_pairs(prices)

        if base == quote:
            return 1

        if (base, quote) not in coin_pairs:
            return 1 / prices[(quote, base)]

        return prices[(base, quote)]


def get_coin_pairs(prices):
    """
    Returns the coin pairs available in the price data.
    """
    if isinstance(prices, DataFrame):
        return tuple(prices.columns)
    if isinstance(prices, Series):
        return tuple(prices.index)
    if isinstance(prices, dict):
        return tuple(prices.keys())

    raise MetricError(
        f"Argument 'price' must be DataFrame, Series, or dict, not {type(prices)}"
    )


def get_numeraire(coins):
    """
    Returns a preferred numeraire from the provided list of coins.
    """
    numeraire = coins[0]
    preferred = ["USDC", "USDT", "CRVUSD", "ETH", "WETH", "CRV"]

    # Heuristic: base coin in pool of derivatives
    base = min(coins, key=len).upper()
    if all(base in c.upper() for c in coins):
        preferred.append(base)

    for coin in coins:
        if coin.upper() in preferred:
            numeraire = coin
            break

    return numeraire


class PricingMetric(PricingMixin, Metric):
    """
    :class:`Metric` with :class:`PricingMixin` functionality.
    """

    def __init__(self, coin_names, **kwargs):
        """
        Parameters
        ----------
        coin_names : iterable of str
            Symbols for the coins used in a simulation. A numeraire is selected from
            the specified coins.

        """
        super().__init__(coin_names)


class PoolPricingMetric(PricingMixin, PoolMetric):
    """
    :class:`PoolMetric` with :class:`PricingMixin` functionality.
    """

    def __init__(self, pool, **kwargs):
        """
        Parameters
        ----------
        pool : SimPool object
            A pool simulation interface. Used to select the pool's configuration from
            :func:`pool_config` and stored as :python:`self._pool` for access during
            metric computations. Number and names of coins derived from pool metadata.
        """
        super().__init__(pool.asset_names, pool=pool)
