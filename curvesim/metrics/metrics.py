"""
Specific metric classes for use in simulations.
"""


__all__ = [
    "ArbMetrics",
    "PoolBalance",
    "PoolVolume",
    "PoolValue",
    "PriceDepth",
    "Timestamp",
]

from copy import deepcopy

from altair import Axis, Scale
from numpy import array, exp, inf, log, timedelta64
from pandas import DataFrame, concat

from curvesim.pool.sim_interface import (
    SimCurveCryptoPool,
    SimCurveMetaPool,
    SimCurvePool,
    SimCurveRaiPool,
)
from curvesim.utils import cache, get_pairs

from .base import Metric, PoolMetric, PoolPricingMetric, PricingMetric


class ArbMetrics(PricingMetric):
    """
    Computes metrics characterizing arbitrage trades: arbitrageur profits, pool fees,
    and post-trade price error between target and pool price.
    """

    @property
    def config(self):
        return {
            "functions": {
                "metrics": self.compute_arb_metrics,
                "summary": {
                    "arb_profit": "sum",
                    "pool_fees": "sum",
                    "price_error": "median",
                },
            },
            "plot": {
                "metrics": {
                    "arb_profit": {
                        "title": f"Daily Arbitrageur Profit (in {self.numeraire})",
                        "style": "time_series",
                        "resample": "sum",
                    },
                    "pool_fees": {
                        "title": f"Daily Pool Fees (in {self.numeraire})",
                        "style": "time_series",
                        "resample": "sum",
                    },
                    "price_error": {
                        "title": "Price Error",
                        "style": "histogram",
                        "encoding": {
                            "x": {
                                "title": "Price Error (binned)",
                                "shorthand": "price_error",
                                "scale": Scale(domain=[0, 0.05], clamp=True),
                            },
                        },
                    },
                },
                "summary": {
                    "arb_profit": {
                        "title": f"Total Arbitrageur Profit (in {self.numeraire})",
                        "style": "point_line",
                    },
                    "pool_fees": {
                        "title": f"Total Pool Fees (in {self.numeraire})",
                        "style": "point_line",
                    },
                    "price_error": {
                        "title": "Price Error (median)",
                        "style": "point_line",
                    },
                },
            },
        }

    def __init__(self, pool, **kwargs):
        super().__init__(pool.asset_names)

    def compute_arb_metrics(self, **kwargs):
        """Computes all metrics for each timestamp in an individual run."""
        price_sample = kwargs["price_sample"]
        trade_data = kwargs["trade_data"]

        prices = DataFrame(price_sample.prices.to_list(), index=price_sample.index)

        profits = self._compute_profits(prices, trade_data.trades)
        price_error = trade_data.price_errors.apply(
            lambda errors: sum(abs(e) for e in errors.values())
        )

        results = concat([profits, price_error], axis=1)
        results.columns = list(self.config["plot"]["metrics"])

        return results

    def _compute_profits(self, price_df, trade_df):  # pylint: disable=too-many-locals
        """
        Computes arbitrageur profits and pool fees for a single row of data (i.e.,
        a single timestamp) in units of the chosen numeraire, `self.numeraire`.
        """
        numeraire = self.numeraire

        profit = []
        for price_row, trade_row in zip(price_df.iterrows(), trade_df):

            timestamp, prices = price_row
            arb_profit = 0
            pool_profit = 0

            for trade in trade_row:
                market_price = self.get_market_price(
                    trade.coin_in, trade.coin_out, prices
                )
                arb = trade.amount_out - trade.amount_in * market_price
                fee = trade.fee

                if trade.coin_out != numeraire:
                    price = self.get_market_price(trade.coin_out, numeraire, prices)
                    arb *= price
                    fee *= price

                arb_profit += arb
                pool_profit += fee

            profit.append(
                {
                    "timestamp": timestamp,
                    "arb_profit": arb_profit / 10**18,
                    "pool_profit": pool_profit / 10**18,
                }
            )

        return DataFrame(profit).set_index("timestamp")


class PoolVolume(PoolPricingMetric):
    """
    Records total trade volume for each timestamp.
    """

    @property
    @cache
    def pool_config(self):
        base = {
            "functions": {"summary": {"pool_volume": "sum"}},
            "plot": {
                "metrics": {
                    "pool_volume": {
                        "title": "Daily Volume",
                        "style": "time_series",
                        "resample": "sum",
                    },
                },
                "summary": {
                    "pool_volume": {
                        "title": "Total Volume",
                        "style": "point_line",
                    },
                },
            },
        }

        functions = {
            SimCurvePool: self.get_stableswap_pool_volume,
            SimCurveMetaPool: self.get_stableswap_metapool_volume,
            SimCurveRaiPool: self.get_stableswap_metapool_volume,
            SimCurveCryptoPool: self.get_cryptoswap_pool_volume,
        }

        units = {
            SimCurvePool: "(of Any Coin)",
            SimCurveMetaPool: "(of Any Coin)",
            SimCurveRaiPool: "(of Any Coin)",
            SimCurveCryptoPool: f"(in {self.numeraire})",
        }

        config = {}
        for pool in functions:
            cfg = deepcopy(base)
            cfg["functions"]["metrics"] = functions[pool]
            _units = units[pool]
            cfg["plot"]["metrics"]["pool_volume"]["title"] = "Daily Volume " + _units
            cfg["plot"]["summary"]["pool_volume"]["title"] = "Total Volume " + _units
            config[pool] = cfg

        return config

    def get_stableswap_pool_volume(self, **kwargs):
        """
        Records trade volume for stableswap non-meta-pools.
        """
        trade_data = kwargs["trade_data"]

        def per_timestamp_function(trade_data):
            trades = trade_data.trades
            return sum(trade.amount_in for trade in trades) / 10**18

        return self._get_volume(trade_data, per_timestamp_function)

    def get_stableswap_metapool_volume(self, **kwargs):
        """
        Records trade volume for stableswap meta-pools. Only includes trades involving
        the meta-asset (basepool-only trades are ignored).
        """
        trade_data = kwargs["trade_data"]

        meta_asset = self._pool.asset_names[0]

        def per_timestamp_function(trade_data):
            volume = 0
            for trade in trade_data.trades:
                if meta_asset in (trade.coin_in, trade.coin_out):
                    volume += trade.amount_in
            return volume / 10**18

        return self._get_volume(trade_data, per_timestamp_function)

    def get_cryptoswap_pool_volume(self, **kwargs):
        """
        Records trade volume for cryptoswap non-meta-pools.
        """
        trades = kwargs["trade_data"].trades
        prices = kwargs["price_sample"].prices

        trade_price_data = concat([trades, prices], axis=1)
        numeraire = self.numeraire

        def per_timestamp_function(trade_price_data):
            trades = trade_price_data.trades
            prices = trade_price_data.prices
            get_price = self.get_market_price

            volume = 0
            for trade in trades:
                volume += trade.amount_in * get_price(trade.coin_in, numeraire, prices)
            return volume / 10**18

        return self._get_volume(trade_price_data, per_timestamp_function)

    def _get_volume(self, trade_data, per_timestamp_function):
        volume = trade_data.apply(per_timestamp_function, axis=1)
        results = DataFrame(volume)
        results.columns = ["pool_volume"]
        return results


class PoolBalance(PoolMetric):
    """
    Computes the pool balance metric, which ranges from 0 (completely imbalanced) to 1
    (completely balanced).
    """

    @property
    @cache
    def pool_config(self):
        ss_config = {
            "functions": {
                "metrics": self.get_pool_balance,
                "summary": {"pool_balance": ["median", "min"]},
            },
            "plot": {
                "metrics": {
                    "pool_balance": {
                        "title": "Pool Balance/Imbalance",
                        "style": "time_series",
                        "resample": "median",
                        "encoding": {
                            "y": {
                                "title": "% Balanced (Daily Median)",
                                "axis": Axis(format="%"),
                            },
                        },
                    }
                },
                "summary": {
                    "pool_balance": {
                        "title": "Pool Balance/Imbalance",
                        "style": "point_line",
                        "encoding": {
                            "y": {"title": "% Balanced", "axis": Axis(format="%")},
                        },
                    }
                },
            },
        }

        return dict.fromkeys(
            [SimCurveMetaPool, SimCurvePool, SimCurveRaiPool, SimCurveCryptoPool],
            ss_config,
        )

    def get_pool_balance(self, **kwargs):
        """
        Computes pool balance metrics for each timestamp in an individual run.
        Used for any Curve pool.
        """
        pool_state = kwargs["pool_state"]
        balance = pool_state.apply(self._compute_stableswap_balance, axis=1)
        return DataFrame(balance, columns=["pool_balance"])

    def _compute_stableswap_balance(self, pool_state_row):
        """
        Computes balance metric for a single row of data (i.e., a single timestamp).
        Used for any Curve pool.
        """
        self.set_pool_state(pool_state_row)
        pool = self._pool

        xp = array(pool._xp())  # pylint: disable=protected-access
        n = pool.n
        bal = 1 - sum(abs(xp / sum(xp) - 1 / n)) / (2 * (n - 1) / n)

        return bal


class PoolValue(PoolPricingMetric):
    """
    Computes pool's value over time in virtual units and the chosen
    numeraire, `self.numeraire`. Each are summarized as annualized returns.
    """

    @property
    @cache
    def pool_config(self):
        plot = {
            "metrics": {
                "pool_value_virtual": {
                    "title": "Pool Value (Virtual)",
                    "style": "time_series",
                    "resample": "last",
                },
                "pool_value": {
                    "title": f"Pool Value (in {self.numeraire})",
                    "style": "time_series",
                    "resample": "last",
                },
            },
            "summary": {
                "pool_value_virtual": {
                    "title": "Annualized Returns (Virtual)",
                    "style": "point_line",
                    "encoding": {"y": {"axis": Axis(format="%")}},
                },
                "pool_value": {
                    "title": f"Annualized Returns (in {self.numeraire})",
                    "style": "point_line",
                    "encoding": {"y": {"axis": Axis(format="%")}},
                },
            },
        }

        summary_fns = {
            "pool_value_virtual": {
                "annualized_returns": self.compute_annualized_returns
            },
            "pool_value": {"annualized_returns": self.compute_annualized_returns},
        }

        base = {
            "functions": {"summary": summary_fns},
            "plot": plot,
        }

        functions = {
            SimCurvePool: self.get_stableswap_pool_value,
            SimCurveMetaPool: self.get_stableswap_metapool_value,
            SimCurveRaiPool: self.get_stableswap_metapool_value,
            SimCurveCryptoPool: self.get_cryptoswap_pool_value,
        }

        config = {}
        for pool, fn in functions.items():
            config[pool] = deepcopy(base)
            config[pool]["functions"]["metrics"] = fn

        return config

    def get_stableswap_pool_value(self, **kwargs):
        """
        Computes all metrics for each timestamp in an individual run.
        Used for non-meta stableswap pools.
        """

        return self._get_pool_value(
            kwargs["pool_state"],
            kwargs["price_sample"],
            self._get_stableswap_virtual_value,
        )

    def get_stableswap_metapool_value(self, **kwargs):
        """
        Computes all metrics for each timestamp in an individual run.
        Used for stableswap metapools.
        """

        return self._get_metapool_value(
            kwargs["pool_state"],
            kwargs["price_sample"],
            self._get_stableswap_virtual_value,
        )

    def get_cryptoswap_pool_value(self, **kwargs):
        """
        Computes all metrics for each timestamp in an individual run.
        Used for non-meta cryptoswap pools.
        """

        return self._get_pool_value(
            kwargs["pool_state"],
            kwargs["price_sample"],
            self._get_cryptoswap_virtual_value,
        )

    def _get_pool_value(self, pool_state, price_sample, virtual_price_fn):
        """
        Computes all metrics for each timestamp in an individual run.
        Used for non-meta pools.
        """
        reserves = DataFrame(
            pool_state.balances.to_list(),
            index=pool_state.index,
            columns=self._pool.coin_names,
        )

        prices = DataFrame(price_sample.prices.to_list(), index=price_sample.index)

        pool_value = self._get_value_from_prices(reserves / 10**18, prices)
        pool_value_virtual = pool_state.apply(virtual_price_fn, axis=1)

        results = concat([pool_value_virtual, pool_value], axis=1)
        results.columns = list(self.config["plot"]["metrics"])
        return results.astype("float64")

    def _get_metapool_value(self, pool_state, price_sample, virtual_price_fn):
        """
        Computes all metrics for each timestamp in an individual run.
        Used for stableswap metapools.
        """
        max_coin = self._pool.max_coin
        pool = self._pool

        meta_reserves = DataFrame(
            pool_state.balances.to_list(),
            index=pool_state.index,
            columns=pool.coin_names,
        )

        base_reserves = DataFrame(
            pool_state.balances_base.to_list(),
            index=pool_state.index,
            columns=pool.basepool.coin_names,
        )

        prices = DataFrame(price_sample.prices.to_list(), index=price_sample.index)

        LP_token_proportion = meta_reserves.iloc[:, max_coin] / pool_state.tokens_base
        base_reserves = base_reserves.mul(LP_token_proportion, axis=0)
        reserves = concat([meta_reserves.iloc[:, :max_coin], base_reserves], axis=1)

        pool_value = self._get_value_from_prices(reserves / 10**18, prices)
        pool_value_virtual = pool_state.apply(virtual_price_fn, axis=1)

        results = concat([pool_value_virtual, pool_value], axis=1)
        results.columns = list(self.config["plot"]["metrics"])
        return results.astype("float64")

    def _get_value_from_prices(self, reserves, prices):
        """
        Computes pool value in the chosen numeraire, `self.numeraire`.
        Can be used for any pool type.
        """
        get_price = self.get_market_price
        numeraire = self.numeraire

        value = 0
        for coin_name in reserves.columns:
            value += reserves[coin_name] * get_price(coin_name, numeraire, prices)
        return value

    def _get_stableswap_virtual_value(self, pool_state_row):
        """
        Computes virtual pool value for a single row of data (i.e., a single timestamp).
        Used for any stableswap pool.
        """
        self.set_pool_state(pool_state_row)
        return self._pool.D() / 10**18

    def _get_cryptoswap_virtual_value(self, pool_state_row):
        """
        Computes virtual pool value for a single row of data (i.e., a single timestamp).
        Used for any cryptoswap pool.
        """
        self.set_pool_state(pool_state_row)
        # pylint: disable-next=protected-access
        return self._pool._get_xcp(self._pool.D) / 10**18

    def compute_annualized_returns(self, data):
        """Computes annualized returns from a series of pool values."""
        year_multipliers = timedelta64(365, "D") / data.index.to_series().diff()
        log_returns = log(data).diff()  # pylint: disable=no-member

        return exp((log_returns * year_multipliers).mean()) - 1


class PriceDepth(PoolMetric):
    """
    Computes metrics indicating a pool's price (liquidity) depth. Generally, uses
    liquidity density, % change in reserves per % change in price.
    """

    @property
    @cache
    def pool_config(self):
        base = {
            "functions": {
                "summary": {"liquidity_density": ["median", "min"]},
            },
            "plot": {
                "metrics": {
                    "liquidity_density": {
                        "title": "Liquidity Density (Daily Median)",
                        "style": "time_series",
                        "resample": "median",
                        "encoding": {
                            "y": {"title": "Liquidity Density (Daily Median)"}
                        },
                    }
                },
                "summary": {
                    "liquidity_density": {
                        "title": "Liquidity Density",
                        "style": "point_line",
                    }
                },
            },
        }

        functions = {
            SimCurvePool: self.get_stableswap_LD,
            SimCurveMetaPool: self.get_stableswap_LD,
            SimCurveRaiPool: self.get_stableswap_LD,
            SimCurveCryptoPool: self.get_cryptoswap_LD,
        }

        config = {}
        for pool, fn in functions.items():
            config[pool] = deepcopy(base)
            config[pool]["functions"]["metrics"] = fn

        return config

    def get_stableswap_LD(self, **kwargs):
        """
        Computes liquidity density for each timestamp in an individual run.
        Used for all Curve stableswap pools.
        """
        pool_state = kwargs["pool_state"]

        def trade_size_function(coin_in):
            x_per_dx = 10**8
            return self._pool.asset_balances[coin_in] // x_per_dx

        return self._get_LD(pool_state, trade_size_function)

    def get_cryptoswap_LD(self, **kwargs):
        """
        Computes liquidity density for each timestamp in an individual run.
        Used for all Curve crpytoswap pools.
        """
        pool_state = kwargs["pool_state"]

        extra_profit = self._pool.allowed_extra_profit  # disable price_scale updates
        self._pool.allowed_extra_profit = inf

        def trade_size_function(coin_in):
            return self._pool.get_min_trade_size(coin_in)

        LD = self._get_LD(pool_state, trade_size_function)
        self._pool.allowed_extra_profit = extra_profit
        return LD

    def _get_LD(self, pool_state, trade_size_function):
        """
        Computes liquidity density for each timestamp in an individual run.
        Used for any sim pool.
        """
        coin_pairs = get_pairs(self._pool.coin_names)  # only meta assets for metapools

        LD = pool_state.apply(
            self._get_LD_by_row,
            axis=1,
            coin_pairs=coin_pairs,
            trade_size_function=trade_size_function,
        )

        return DataFrame(LD, columns=["liquidity_density"])

    def _get_LD_by_row(self, pool_state_row, coin_pairs, trade_size_function):
        """
        Computes liquidity density for a single row of data (i.e., a single timestamp).
        Used for any sim pool.
        """
        self.set_pool_state(pool_state_row)
        pool = self._pool

        LD = []
        for pair in coin_pairs:
            amount_in = [trade_size_function(coin) for coin in pair]
            LD_i = _compute_liquidity_density(pool, *pair, amount_in[0])
            LD_j = _compute_liquidity_density(pool, *reversed(pair), amount_in[1])
            LD += [LD_i, LD_j]
        return sum(LD) / len(LD)


def _compute_liquidity_density(pool, coin_in, coin_out, amount_in):
    """
    Computes liquidity density for a single pair of coins.
    """
    x_avg = pool.asset_balances[coin_in] + amount_in / 2
    price_pre = pool.price(coin_in, coin_out, use_fee=False)
    price_post = _post_trade_price(pool, coin_in, coin_out, amount_in)
    LD = amount_in * (price_pre + price_post) / (2 * (price_pre - price_post) * x_avg)
    return LD


def _post_trade_price(pool, coin_in, coin_out, amount_in, use_fee=False):
    """
    Computes price after executing a trade of size amount_in.
    """
    with pool.use_snapshot_context():
        pool.trade(coin_in, coin_out, amount_in)
        price = pool.price(coin_in, coin_out, use_fee=use_fee)

    return price


class Timestamp(Metric):
    """Simple pass-through metric to record timestamps."""

    @property
    def config(self):
        return {"functions": {"metrics": self._get_timestamp}}

    def _get_timestamp(self, **kwargs):
        price_sample = kwargs["price_sample"]
        return DataFrame(price_sample.timestamp)
