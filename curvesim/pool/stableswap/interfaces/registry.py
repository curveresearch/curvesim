interface_functions = (
    "price",
    "trade",
    "test_trade",
    "make_error_fns",
    "precisions",
    "_get_pool_state",  # required
    "_init_coin_indices",  # required
)


_STABLESWAP_INTERFACE_FUNCTIONS = {}

_STABLESWAP_PRICING_FUNCTIONS = {}


def register_interface(pool_type, functions, pricing_functions):
    func_dict = dict(zip(interface_functions, functions))
    _STABLESWAP_INTERFACE_FUNCTIONS[pool_type] = func_dict
    _STABLESWAP_PRICING_FUNCTIONS[pool_type] = pricing_functions


def get_stableswap_interface_functions(pool_type):
    return _STABLESWAP_INTERFACE_FUNCTIONS[pool_type]


def get_stableswap_pricing_functions(pool_type):
    return _STABLESWAP_PRICING_FUNCTIONS[pool_type]
