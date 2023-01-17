import time


def get_unix_timestamp():
    """Get the timestamp in Unix time."""
    return int(time.time())


class CurveCryptoPool:
    def __init__(
        self,
        A: int,
        gamma: int,
        mid_fee: int,
        out_fee: int,
        allowed_extra_profit: int,
        fee_gamma: int,
        adjustment_step: int,
        admin_fee: int,
        ma_half_time: int,
        initial_price: int,
        token,
        coins,
        precisions,
    ):
        self.A = A
        self.gamma = gamma

        self.mid_fee = mid_fee
        self.out_fee = out_fee
        self.allowed_extra_profit = allowed_extra_profit
        self.fee_gamma = fee_gamma
        self.adjustment_step = adjustment_step
        self.admin_fee = admin_fee

        self.price_scale = initial_price
        self._price_oracle = initial_price
        self.last_prices = initial_price
        self.last_prices_timestamp = get_unix_timestamp()
        self.ma_half_time = ma_half_time

        self.xcp_profit_a = 10**18

        self.token = token
        self.coins = coins
        self.PRECISIONS = precisions

        if len(coins) != len(precisions):
            raise ValueError("`coins` must have same length as `precisions`")

        self.n = len(coins)
