from curvesim.logging import get_logger
from curvesim.pool.cryptoswap.calcs import newton_D

from .base import PoolMetaDataBase

logger = get_logger(__name__)


class CryptoswapMetaData(PoolMetaDataBase):
    """Specific implementation of the `PoolMetaDataInterface` for Cryptoswap."""

    def init_kwargs(self, balanced=True, balanced_base=True, normalize=True):
        data = self._dict

        kwargs = {
            "A": data["params"]["A"],
            "gamma": data["params"]["gamma"],
            "n": len(data["coins"]["names"]),
            "D": data["reserves"]["D"],
            "mid_fee": data["params"]["mid_fee"],
            "out_fee": data["params"]["out_fee"],
            "allowed_extra_profit": data["params"]["allowed_extra_profit"],
            "fee_gamma": data["params"]["fee_gamma"],
            "adjustment_step": data["params"]["adjustment_step"],
            "price_scale": data["params"]["price_scale"],
            "admin_fee": data["params"]["admin_fee"],
            "ma_half_time": data["params"]["ma_half_time"],
            "tokens": data["reserves"]["tokens"],
            "xcp_profit": data["params"]["xcp_profit"],
            "xcp_profit_a": data["params"]["xcp_profit_a"],
        }
        n = kwargs["n"]

        if not normalize:
            kwargs["precisions"] = [10 ** (18 - d) for d in data["coins"]["decimals"]]
        else:
            kwargs["precisions"] = [1] * n

        if not balanced:
            if normalize:
                coin_balances = data["reserves"]["by_coin"]
            else:
                coin_balances = data["reserves"]["unnormalized_by_coin"]
            kwargs["balances"] = coin_balances

        # Aug 15, 2023
        #
        # This is fallback logic for missing subgraph functionality.  Right now
        # the subgraph will return 0 for crypto pools with more than 2 coins.
        # ETA for fix is expected to be within few weeks.
        #
        # Using the staging subgraph should suffice for tricrypto-ng factory pools.
        if n == 3:
            if len(kwargs["price_scale"]) != 2:
                logger.warning("Price scale is missing.  Using ad-hoc setting.")
                coin_balances = data["reserves"]["by_coin"]
                numeraire_balance = coin_balances[0]
                price_scale = [
                    numeraire_balance * 10**18 // coin_balances[1],
                    numeraire_balance * 10**18 // coin_balances[2],
                ]
                kwargs["price_scale"] = price_scale

                A = kwargs["A"]
                gamma = kwargs["gamma"]
                xp = [
                    coin_balances[0],
                    coin_balances[0],
                    coin_balances[0],
                ]

                D = newton_D(A, gamma, xp)
                kwargs["D"] = D

        # Due to outstanding subgraph bug, we need to do something for
        # the missing value.
        if not kwargs["ma_half_time"]:
            kwargs["ma_half_time"] = 600

        return kwargs

    @property
    def coins(self):
        return self._dict["coins"]["addresses"]

    @property
    def coin_names(self):
        return self._dict["coins"]["names"]

    @property
    def n(self):
        return len(self._dict["coins"]["names"])
