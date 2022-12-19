__all__ = [
    "register_interface",
    "get_stableswap_interface_functions",
    "get_stableswap_pricing_functions",
]

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


def register_interface(pool_type, functions_module, pricing_functions):
    func_dict = {}
    for interface_func_name in interface_functions:
        if hasattr(functions_module, interface_func_name):
            func_dict[interface_func_name] = getattr(
                functions_module, interface_func_name
            )
    _STABLESWAP_INTERFACE_FUNCTIONS[pool_type] = func_dict
    _STABLESWAP_PRICING_FUNCTIONS[pool_type] = pricing_functions


def get_stableswap_interface_functions(pool_type):
    return _STABLESWAP_INTERFACE_FUNCTIONS[pool_type]


def get_stableswap_pricing_functions(pool_type):
    return _STABLESWAP_PRICING_FUNCTIONS[pool_type]
