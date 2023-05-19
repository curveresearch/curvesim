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

from functools import partial

from altair import Axis, Scale
from numpy import array, exp, log
from pandas import DataFrame, concat

from curvesim.pool.sim_interface import SimCurveMetaPool, SimCurvePool, SimCurveRaiPool
from curvesim.utils import cache, get_pairs
from .base import Metric, PoolMetric, PricingMetric, PoolPricingMetric


class ArbMetrics(PricingMetric):
    """
    Computes metrics characterizing arbitrage trades: arbitrageur profits, pool fees,
    trade volume, and post-trade price error between target and pool price.
    """

    @property
    def config(self):
        return {
            "functions": {
                "metrics": self.compute_arb_metrics,
                "summary": {
                    "arb_profit": "sum",
                    "pool_fees": "sum",
                    "pool_volume": "sum",
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
                    "pool_volume": {
                        "title": "Daily Volume",
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
                    "pool_volume": {
                        "title": "Total Volume",
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
        coin_names = list(pool.coin_indices.keys())
        super().__init__(coin_names, pool.n_total)

    def compute_arb_metrics(self, price_sample, trade_data, **kwargs):
        """Computes all metrics for each timestamp in an individual run."""

        data = concat([price_sample.prices, trade_data], axis=1)

        profits = data.apply(self._compute_profits, axis=1, result_type="expand")
        volume = data.volume / 10**18
        price_error = data.price_errors.abs().apply(sum)

        results = concat([profits, volume, price_error], axis=1)
        results.columns = list(self.config["plot"]["metrics"])
        return results

    def _compute_profits(self, data_row):
        """
        Computes arbitrageur profits and pool fees for a single row of data (i.e.,
        a single timestamp) in units of the chosen numeraire, `self.numeraire`.
        """
        get_price = self.get_market_price
        num_idx = self.numeraire_idx
        prices = data_row.prices

        arb_profit = 0
        pool_profit = 0
        for trade in data_row.trades:
            i, j, dx, dy, fee = trade
            arb = dy - dx * get_price(i, j, prices)

            if j != num_idx:
                price = get_price(j, num_idx, prices)
                arb = arb * price
                fee = fee * price

            arb_profit += arb / 10**18
            pool_profit += fee / 10**18

        return arb_profit, pool_profit


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

    __slots__ = ["_freq"]

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

    def __init__(self, pool, freq, **kwargs):
        self._freq = freq
        super().__init__(pool)

    def get_stableswap_pool_value(self, pool_state, price_sample, **kwargs):
        """
        Computes all metrics for each timestamp in an individual run.
        Used for non-meta stableswap pools.
        """
        reserves = DataFrame(pool_state.balances.to_list())
        prices = DataFrame(price_sample.prices.to_list())

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
        meta_reserves = DataFrame(pool_state.balances.to_list())
        base_reserves = DataFrame(pool_state.balances_base.to_list())
        prices = DataFrame(price_sample.prices.to_list())
        max_coin = self._pool.max_coin

        LP_token_proportion = meta_reserves[max_coin] / pool_state.tokens_base
        base_reserves = base_reserves.mul(LP_token_proportion, axis=0)
        reserves = concat([meta_reserves.iloc[:, :max_coin], base_reserves], axis=1)
        reserves.columns = range(len(reserves.columns))

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
        num_idx = self.numeraire_idx

        value = 0
        for i in reserves.columns:  # columns are ordered range of ints
            value += reserves[i] * get_price(i, num_idx, prices)

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
        log_returns = log(data).diff()  # pylint: disable=no-member
        year_mult = 60 / self._freq * 24 * 365
        return exp(log_returns.mean() * year_mult) - 1


class PriceDepth(PoolMetric):
    """
    Computes metrics indicating a pool's price (liquidity) depth. Generally, uses
    liquidity density, % change in reserves per % change in price.
    """

    __slots__ = ["_factor"]

    @property
    def pool_config(self):
        ss_plot = {
            "metrics": {
                "liquidity_density": {
                    "title": "Liquidity Density",
                    "style": "time_series",
                    "resample": "median",
                    "encoding": {"y": {"title": "Liquidity Density (Daily Median)"}},
                }
            },
            "summary": {
                "liquidity_density": {
                    "title": "Liquidity Density",
                    "style": "point_line",
                }
            },
        }

        ss_summary_fns = {"liquidity_density": ["median", "min"]}

        return {
            SimCurvePool: {
                "functions": {
                    "metrics": self.get_curve_pool_LD,
                    "summary": ss_summary_fns,
                },
                "plot": ss_plot,
            },
            SimCurveMetaPool: {
                "functions": {
                    "metrics": self.get_curve_metapool_LD,
                    "summary": ss_summary_fns,
                },
                "plot": ss_plot,
            },
            SimCurveRaiPool: {
                "functions": {
                    "metrics": self.get_curve_metapool_LD,
                    "summary": ss_summary_fns,
                },
                "plot": ss_plot,
            },
        }

    def __init__(self, pool, factor=10**8, **kwargs):
        self._factor = factor
        super().__init__(pool)

    def get_curve_pool_LD(self, pool_state, **kwargs):
        """
        Computes liquidity density for each timestamp in an individual run, averaging
        across all coin pairs. Used for non-meta stableswap pools.
        """
        index_combos = self._curve_pool_index_combos
        return self._get_curve_LD(index_combos, pool_state)

    def get_curve_metapool_LD(self, pool_state, **kwargs):
        """
        Computes liquidity density for each timestamp in an individual run, using only
        top-level coin pairs in a metapool. Used for Curve metapools.
        """
        index_combos = self._curve_metapool_index_combos
        return self._get_curve_LD(index_combos, pool_state)

    def _get_curve_LD(self, index_combos, pool_state):
        """
        Computes liquidity density for each timestamp in an individual run.
        Used for all Curve pools.
        """
        get_LD = partial(self._get_curve_LD_by_row, index_combos=index_combos)
        LD = pool_state.apply(get_LD, axis=1)
        return DataFrame(LD, columns=["liquidity_density"])

    def _get_curve_LD_by_row(self, pool_state_row, index_combos):
        """
        Computes liquidity density for a single row of data (i.e., a single timestamp).
        Used for all Curve pools.
        """
        self.set_pool_state(pool_state_row)
        LD = []
        for i, j in index_combos:
            ld = self._compute_liquidity_density(i, j)
            LD.append(ld)
        return sum(LD) / len(LD)

    @property
    @cache
    def _curve_pool_index_combos(self):
        """Returns all pairwise combinations of coin indices."""
        return get_pairs(self._pool.n)

    @property
    @cache
    def _curve_metapool_index_combos(self):
        """
        Returns pairwise combinations of coin indices in the top level of a metapool.

        Our convention for the basepool LP token index is to use
        the total number of stablecoins (including basepool).
        This removes ambiguity as it is one "off the end" and thus
        either doesn't exist or is the basepool LP token.
        """
        pool = self._pool
        base_idx = list(range(pool.n))
        base_idx[pool.max_coin] = pool.n_total
        return get_pairs(base_idx)

    def _compute_liquidity_density(self, coin_in, coin_out):
        """
        Computes liquidity density for a single pair of coins.

        Only for top-level liquidity density.  Cannot compare between
        coins in basepool and primary stablecoin in metapool.
        """
        factor = self._factor
        pool = self._pool

        price_pre = pool.price(coin_in, coin_out, use_fee=False)
        price_post = pool.test_trade(coin_in, coin_out, factor, use_fee=False)
        LD1 = price_pre / ((price_pre - price_post) * factor)

        price_pre = pool.price(coin_out, coin_in, use_fee=False)
        # pylint: disable-next=arguments-out-of-order
        price_post = pool.test_trade(coin_out, coin_in, factor, use_fee=False)
        LD2 = price_pre / ((price_pre - price_post) * factor)

        return (LD1 + LD2) / 2


class Timestamp(Metric):
    """Simple pass-through metric to record timestamps."""

    @property
    def config(self):
        return {"functions": {"metrics": self._get_timestamp}}

    def _get_timestamp(self, price_sample, **kwargs):
        return DataFrame(price_sample.timestamp)
