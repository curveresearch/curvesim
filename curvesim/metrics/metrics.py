"""
Specific metric classes for use in simulations.
"""


__all__ = [
    "ArbMetrics",
    "PoolBalance",
    "PoolValue",
    "PriceDepth",
    "Timestamp",
]

from copy import deepcopy

from altair import Axis, Scale
from numpy import array, exp, log, timedelta64
from pandas import DataFrame, concat

from curvesim.pool.sim_interface import SimCurveMetaPool, SimCurvePool, SimCurveRaiPool
from curvesim.utils import get_pairs

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
        super().__init__(pool.assets.symbols)

    def compute_arb_metrics(self, price_sample, trade_data, **kwargs):
        """Computes all metrics for each timestamp in an individual run."""

        prices = DataFrame(price_sample.prices.to_list(), index=price_sample.index)

        profits = self._compute_profits(prices, trade_data.trades)
        price_error = trade_data.price_errors.apply(
            lambda errors: sum(abs(e) for e in errors)
        )

        results = concat([profits, price_error], axis=1)
        results.columns = list(self.config["plot"]["metrics"])

        return results

    def _compute_profits(self, price_df, trade_df):
        """
        Computes arbitrageur profits and pool fees for a single row of data (i.e.,
        a single timestamp) in units of the chosen numeraire, `self.numeraire`.
        """
        get_price = self.get_market_price
        numeraire = self.numeraire

        profit = []
        for price_row, trade_row in zip(price_df.iterrows(), trade_df):

            timestamp, prices = price_row
            arb_profit = 0
            pool_profit = 0

            for trade in trade_row:
                market_price = get_price(trade.coin_in, trade.coin_out, prices)
                arb = trade.amount_out - trade.amount_in * market_price
                fee = trade.fee

                if trade.coin_out != numeraire:
                    price = get_price(trade.coin_out, numeraire, prices)
                    arb = arb * price
                    fee = fee * price

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


class PoolVolume(PoolMetric):
    """
    Records total trade volume for each timestamp.
    """

    @property
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
        }

        config = {}
        for pool, fn in functions.items():
            config[pool] = deepcopy(base)
            config[pool]["functions"]["metrics"] = fn

        return config

    def get_stableswap_pool_volume(self, trade_data, **kwargs):
        """
        Records trade volume for stableswap non-meta-pools.
        """

        def per_timestamp_function(trades):
            return sum([trade.amount_in for trade in trades]) / 10**18

        return self._get_volume(trade_data, per_timestamp_function)

    def get_stableswap_metapool_volume(self, trade_data, **kwargs):
        """
        Records trade volume for stableswap meta-pools. Only includes trades involving
        the meta-asset (basepool-only trades are ignored).
        """

        meta_asset = self._pool.assets.symbols[0]

        def per_timestamp_function(trades):
            volume = 0
            for trade in trades:
                if meta_asset in (trade.coin_in, trade.coin_out):
                    volume += trade.amount_in
            return volume / 10**18

        return self._get_volume(trade_data, per_timestamp_function)

    def _get_volume(self, trade_data, per_timestamp_function):
        trades = trade_data.trades
        volume = trades.apply(per_timestamp_function)
        results = DataFrame(volume)
        results.columns = ["pool_volume"]
        return results


class PoolBalance(PoolMetric):
    """
    Computes the pool balance metric, which ranges from 0 (completely imbalanced) to 1
    (completely balanced).
    """

    @property
    def pool_config(self):
        ss_config = {
            "functions": {
                "metrics": self.get_stableswap_balance,
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
            [SimCurveMetaPool, SimCurvePool, SimCurveRaiPool], ss_config
        )

    def get_stableswap_balance(self, pool_state, **kwargs):
        """
        Computes pool balance metrics for each timestamp in an individual run.
        Used for any stableswap pool.
        """
        balance = pool_state.apply(self._compute_stableswap_balance, axis=1)
        return DataFrame(balance, columns=["pool_balance"])

    def _compute_stableswap_balance(self, pool_state_row):
        """
        Computes balance metric for a single row of data (i.e., a single timestamp).
        Used for any stableswap pool.
        """
        self.set_pool_state(pool_state_row)
        pool = self._pool

        xp = array(pool._xp())
        n = pool.n
        bal = 1 - sum(abs(xp / sum(xp) - 1 / n)) / (2 * (n - 1) / n)

        return bal


class PoolValue(PoolPricingMetric):
    """
    Computes pool's value over time in virtual units and the chosen
    numeraire, `self.numeraire`. Each are summarized as annualized returns.
    """

    @property
    def pool_config(self):
        ss_plot = {
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

        ss_summary_fns = {
            "pool_value_virtual": {
                "annualized_returns": self.compute_annualized_returns
            },
            "pool_value": {"annualized_returns": self.compute_annualized_returns},
        }

        return {
            SimCurvePool: {
                "functions": {
                    "metrics": self.get_stableswap_pool_value,
                    "summary": ss_summary_fns,
                },
                "plot": ss_plot,
            },
            SimCurveMetaPool: {
                "functions": {
                    "metrics": self.get_stableswap_metapool_value,
                    "summary": ss_summary_fns,
                },
                "plot": ss_plot,
            },
            SimCurveRaiPool: {
                "functions": {
                    "metrics": self.get_stableswap_metapool_value,
                    "summary": ss_summary_fns,
                },
                "plot": ss_plot,
            },
        }

    def get_stableswap_pool_value(self, pool_state, price_sample, **kwargs):
        """
        Computes all metrics for each timestamp in an individual run.
        Used for non-meta stableswap pools.
        """
        reserves = DataFrame(
            pool_state.balances.to_list(),
            index=pool_state.index,
            columns=self._pool.coin_names,
        )

        prices = DataFrame(price_sample.prices.to_list(), index=price_sample.index)

        pool_value = self._get_value_from_prices(reserves / 10**18, prices)
        pool_value_virtual = pool_state.apply(
            self._get_stableswap_virtual_value, axis=1
        )

        results = concat([pool_value_virtual, pool_value], axis=1)
        results.columns = list(self.config["plot"]["metrics"])
        return results.astype("float64")

    def get_stableswap_metapool_value(self, pool_state, price_sample, **kwargs):
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
        pool_value_virtual = pool_state.apply(
            self._get_stableswap_virtual_value, axis=1
        )

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

    def compute_annualized_returns(self, data):
        """Computes annualized returns from a series of pool values."""
        year_multipliers = timedelta64(1, "Y") / data.index.to_series().diff()
        log_returns = log(data).diff()  # pylint: disable=no-member

        return exp((log_returns * year_multipliers).mean()) - 1


class PriceDepth(PoolMetric):
    """
    Computes metrics indicating a pool's price (liquidity) depth. Generally, uses
    liquidity density, % change in reserves per % change in price.
    """

    __slots__ = ["_factor"]

    @property
    def pool_config(self):
        ss_config = {
            "functions": {
                "metrics": self.get_curve_LD,
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

        return dict.fromkeys(
            [SimCurveMetaPool, SimCurvePool, SimCurveRaiPool], ss_config
        )

    def __init__(self, pool, factor=10**8, **kwargs):
        self._factor = factor
        super().__init__(pool)

    def get_curve_LD(self, pool_state, **kwargs):
        """
        Computes liquidity density for each timestamp in an individual run.
        Used for all Curve pools.
        """
        coin_pairs = get_pairs(
            self._pool.coin_names
        )  # for metapool, uses only meta assets
        LD = pool_state.apply(self._get_curve_LD_by_row, axis=1, coin_pairs=coin_pairs)
        return DataFrame(LD, columns=["liquidity_density"])

    def _get_curve_LD_by_row(self, pool_state_row, coin_pairs):
        """
        Computes liquidity density for a single row of data (i.e., a single timestamp).
        Used for all Curve pools.
        """
        self.set_pool_state(pool_state_row)

        LD = []
        for pair in coin_pairs:
            ld = self._compute_liquidity_density(*pair)
            LD.append(ld)
        return sum(LD) / len(LD)

    def _compute_liquidity_density(self, coin_in, coin_out):
        """
        Computes liquidity density for a single pair of coins.
        """
        factor = self._factor
        pool = self._pool
        post_trade_price = self._post_trade_price

        price_pre = pool.price(coin_in, coin_out, use_fee=False)
        price_post = post_trade_price(pool, coin_in, coin_out, factor)
        LD1 = price_pre / ((price_pre - price_post) * factor)

        price_pre = pool.price(coin_out, coin_in, use_fee=False)
        # pylint: disable-next=arguments-out-of-order
        price_post = post_trade_price(pool, coin_out, coin_in, factor)
        LD2 = price_pre / ((price_pre - price_post) * factor)

        return (LD1 + LD2) / 2

    @staticmethod
    def _post_trade_price(pool, coin_in, coin_out, factor, use_fee=False):
        """
        Computes price after executing a trade of size coin_in balances / factor.
        """

        size = pool.asset_balances[coin_in] // factor

        with pool.use_snapshot_context():
            pool.trade(coin_in, coin_out, size)
            price = pool.price(coin_in, coin_out, use_fee=use_fee)

        return price


class Timestamp(Metric):
    """Simple pass-through metric to record timestamps."""

    @property
    def config(self):
        return {"functions": {"metrics": self._get_timestamp}}

    def _get_timestamp(self, price_sample, **kwargs):
        return DataFrame(price_sample.timestamp)
