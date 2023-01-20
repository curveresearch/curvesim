import time

ADMIN_ACTIONS_DELAY = 3 * 86400
MIN_RAMP_TIME = 86400

MAX_ADMIN_FEE = 10 * 10**9
MIN_FEE = 5 * 10**5  # 0.5 bps
MAX_FEE = 10 * 10**9
MAX_A_CHANGE = 10
NOISE_FEE = 10**5  # 0.1 bps

MIN_GAMMA = 10**10
MAX_GAMMA = 2 * 10**16


EXP_PRECISION = 10**10

N_COINS = 2
PRECISION = 10**18  # The precision to convert to
A_MULTIPLIER = 10000

MIN_A = N_COINS**N_COINS * A_MULTIPLIER / 10
MAX_A = N_COINS**N_COINS * A_MULTIPLIER * 100000


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

        self.balances = [0] * self.n
        self.D = 0

        self.xcp_profit = 0
        self.xcp_profit_a = 0  # Full profit at last claim of admin fees
        # Cached (fast to read) virtual price also used internally
        self.virtual_price = 0
        self.not_adjusted = False
