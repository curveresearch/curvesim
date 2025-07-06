from curvesim.logging import get_logger

from .base import PoolMetaDataBase

logger = get_logger(__name__)


class CryptoswapMetaData(PoolMetaDataBase):
    """Specific implementation of the `PoolMetaDataInterface` for Cryptoswap."""

    def init_kwargs(self, normalize=True):
        data = self._dict
        logger.info(data)
        try:
            virtual_price = data["reserves"]["virtual_price"]  # subgraph format
        except:
            virtual_price = data["params"]["virtual_price"]  # curve prices format

        kwargs = {
            "A": data["params"]["A"],
            "gamma": data["params"]["gamma"],
            "n": len(data["coins"]["names"]),
            "mid_fee": data["params"]["mid_fee"],
            "out_fee": data["params"]["out_fee"],
            "allowed_extra_profit": data["params"]["allowed_extra_profit"],
            "fee_gamma": data["params"]["fee_gamma"],
            "adjustment_step": data["params"]["adjustment_step"],
            "price_scale": data["params"]["price_scale"],
            "admin_fee": data["params"]["admin_fee"],
            "ma_half_time": data["params"]["ma_half_time"],
            "virtual_price": virtual_price,
            "xcp_profit": data["params"]["xcp_profit"],
            "xcp_profit_a": data["params"]["xcp_profit_a"],
        }
        n = kwargs["n"]

        if not normalize:
            kwargs["precisions"] = [10 ** (18 - d) for d in data["coins"]["decimals"]]
        else:
            kwargs["precisions"] = [1] * n

        if normalize:
            coin_balances = data["reserves"]["by_coin"]
        else:
            coin_balances = data["reserves"]["unnormalized_by_coin"]
        kwargs["balances"] = coin_balances

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
