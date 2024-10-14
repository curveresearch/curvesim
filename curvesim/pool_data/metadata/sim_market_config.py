from typing import Union, Optional, Any, Dict
from datetime import datetime # TODO remove?
from time import time
from copy import deepcopy

import gin

from curvesim.utils import dataclass
from curvesim.constants import Chain, CurvePreset
from curvesim.exceptions import CurvesimTypeError, CurvesimValueError
from curvesim.utils import Address, is_address, to_address
from curvesim.pipelines.common.get_pool_data import _parse_timestamp # TODO don't need
#from curvesim.pipelines.common import get_pool_data

#from . import PoolMetaDataInterface


# TODO: consider moving everything to curvesim.pipelines.simulation.py or curvesim.pipelines or curvesim.pipelines.common
@gin.register
class SimMarketConfig:
    """
    class for config, one per simmarket (regardless of # of simmarket per run) (so same simmarket config is reusable)
    treat it as read-only after instantiation
    """
    def __init__(
        self,
        key_metadata: Union[str, dict, PoolMetaDataInterface],
        overrides: dict[str, list[Any]] = {},
        include_template: bool = True,
        chain: Union[str, Chain] = "mainnet",
        balanced: bool = True,
        balanced_base: bool = True,
        end_ts: Union[int, datetime, None] = None, #TODO rethink necessity
    ):
        """
        Parameters
        ----------
        key_metadata : Union[str, dict, PoolMetaDataInterface]
            address, preset name, meta dict, meta class

        overrides : dict[str, list[Any]], optional
            TODO
            should be like pool param iterator's variable_params: 
            dict[str, list[Any]] = {"value1": [...], "value2" : [...], etc.}

            if doing overrides the parameterizedpooliterator way, no need to specify # of runs; # of runs = product of number of overrides for each varaible param
            overrides should be unique

        include_template: bool, optional
        
        chain

        balanced


        balanced_base


        end_ts

        TODO: pool_ts param like in pipeline()?
        """
        if not isinstance(key_metadata, (str, dict, PoolMetaDataInterface)):
            raise CurvesimTypeError(f"{key_metadata} TODO")

        if isinstance(
            key_metadata, str
        ):  # address and strenum will resolve to str type
            if is_address(key_metadata, checksum=False):
                key_metadata = to_address(key_metadata)
            else:
                try:
                    key_metadata = CurvePreset(key_metadata)
                except ValueError:
                    raise CurvesimValueError(
                        f"TODO {key_metadata} - str but not valid address or preset name"
                    )

        if isinstance(overrides, dict):
            not_str = list(filter(lambda key: not isinstance(key, str), overrides.keys()))
            if not_str != []:
                raise CurvesimValueError(f"need str keys {not_str}")

            # just tell user not to use duplicates in any list
            # want a fixed value (diff from template value)? - provide exactly one value - will be used for all sims
        else:
            raise CurvesimTypeError(f"overrides needs dict {overrides}")

        self.key_metadata: Union[Address, CurvePreset, dict, PoolMetaDataInterface] = key_metadata # sim context will handle parsing diff key metadata types
        self.overrides: dict[str, list[Any]] = overrides
        self.include_template: bool = include_template
        self.chain: Chain = Chain(chain)
        self.balanced: bool = balanced
        self.balanced_base: bool = balanced_base
        self.end_ts: Optional[int] = _parse_timestamp(end_ts)


# if not isinstance(metadata, (str, dict, PoolMetaDataInterface)):
#     raise CurvesimTypeError

# if isinstance(metadata, str):
#     if is_address(metadata, checksum=False):
#         metadata = {"address": to_address(metadata)}
#     else:
#         raise CurvesimValueError

# if isinstance(metadata, dict):
#     if "address" in metadata:
#         metadata["address"] = to_address(metadata["address"])

#     if "address" in metadata and all([key in dict_id_1 for key in metadata]):
#         config_base = deepcopy(metadata)
#         _a(config_base)
#     elif all([key in dict_id_2 for key in metadata]) and all([key in metadata for key in dict_id_2]):
#         config_base = deepcopy(metadata)
#         _b(metadata)
#     elif "preset" in metadata and all([key in dict_id_3 for key in metadata]):
#         config_base = deepcopy(metadata)
#         _c(config_base)
#     else:
#         raise CurvesimValueError

# if isinstance(metadata, PoolMetaDataInterface):
#     config_base = metadata

# self._config_base = config_base

# call config_to_metadata and config_to_sim_market right here? (cached after)

# take in any of the below types for key_metadata in init, create "full" value for its type and store in attr _config_base, move configtometadata and configtosimmarket to this class? and expose poolmetadatabase and simmarket as cached properties using those functions (which take include_template and overrides into account)


# keep overrides and include_template above as init params
address = str # this maps to dict below

dict_id_1 = {
    "address": str,
    "chain": str,
    "balanced": bool,
    "balanced_base": bool,
    "timestamp": int,
} # chain, balanced, balanced_base, timestamp not required
# unique id: any subset of this dict containing "address"

def _a(dict_type: dict) -> None:
    if not ("address" in dict_type) or not (isinstance(dict_type["address"], str)):
        raise CurvesimValueError(f"") # TODO

    optional_keys = ["chain", "balanced", "balanced_base", "timestamp"]
    defaults = {"chain": "mainnet", "balanced": True, "balanced_base": True, "timestamp": int(time())}

    for key in defaults:
        if dict_type.get(key) == None:
            dict_type.update((key, defaults[key]))
        else:
            value = dict_type[key]
            expected_type = dict_id_1[key]
            if not isinstance(value, expected_type):
                raise CurvesimValueError(f"SimMarketConfig key_metadata {key}:{value} - expected type {expected_type}") # TODO



dict_id_2 = {
    "name": str,
    "address": str,
    "chain": str,
    "symbol": str,
    "pool_type": str,
    "params": dict,
    "coins": dict, # {"names": list, "addresses": list, "decimals": list,}
    "reserves": dict, # {"by_coin": list, "unnormalized_by_coin": list, }
    "basepool": Optional[dict], 
    "timestamp": int,
} # everything required (to avoid network call)
# unique id: contains exactly these config_base = function(metadata)

def _b(dict_type: dict) -> None:
    if not(all([key in dict_id_2 for key in dict_type]) and all([key in dict_type for key in dict_id_2])):
        raise CurvesimValueError(f"") # TODO

    for key in dict_type:
        value = dict_type[key]
        expected_type = dict_id_2[key]
        if not isinstance(value, expected_type):
            raise CurvesimValueError(f"") # TODO

dict_id_3 = {
    "name": Optional[str],
    "address": Optional[str],
    "chain": Optional[str],
    "symbol": Optional[str],
    "coins": Optional[dict], # {"names": list, "addresses": list, "decimals": list, "prices": list,}
    "tvl": Optional[float],
    "preset": str,
    "basepool": Optional[str], # deployed contracts only, if used
    "timestamp": Optional[int],
}
# unique id: contains "preset", error raising will handle the finer details

# offline function
def _c(dict_type: dict) -> None:
    try:
        preset: str = dict_type["preset"].lower()
        preset_check: CurvePreset = CurvePreset(preset)
        dict_type["preset"] = preset.lower()
    except ValueError as e: # not a CurvePreset
        raise CurvesimValueError(f"") from e # TODO
    except KeyError as e: # "preset" not in dict_type
        raise CurvesimValueError(f"") from e # TODO

    for key in dict_type:
        value = dict_type[key]
        expected_type = dict_id_3[key]
        if not isinstance(value, expected_type):
            raise CurvesimValueError(f"") # TODO
        
    knowable_defaults = {
        "name": None, 
        "address": None,
        "chain": "mainnet",
        "symbol": None,
        "coins": {
            "names": None,
            "addresses": None,
            "decimals": None,
            "prices": None,
        },
        "tvl": None,
        "preset": None,
        "basepool": None,
        "timestamp": int(time()),
    }

    for key in knowable_defaults:
        if not key in dict_type:
            value = knowable_defaults[key]
            dict_type.update((key, value))

        if key == "coins":
            for param in knowable_defaults["coins"]:
                if not param in dict_type["coins"]:
                    dict_type["coins"].update((param, knowable_defaults["coins"][param]))

    deployed_pool: bool = dict_type["address"] != None

    tvl_given: bool = dict_type["tvl"] != None

    deployed_coins: bool = isinstance(dict_type["coins"]["addresses"], list) and tvl_given

    no_contracts: bool = isinstance(dict_type["coins"]["names"], list) and isinstance(dict_type["coins"]["prices"], list)
    no_contracts = no_contracts and tvl_given

    if deployed_pool:
        dict_type.update(("use internet", "deployed pool"))
    elif deployed_coins:
        dict_type.update(("use internet", "deployed coins"))
    elif no_contracts:
        dict_type.update(("use internet", "nothing"))
    else:
        raise CurvesimValueError(f"") # TODO

# create_preset_metadata() - preset_to_curvesim_dict
# preset - required
    # infer pool type - explicit mapping from preset name
    # infer stableswap/cryptoswap by mapping from preset name
# tvl - optional - assume balanced - precisions and pricing data matter
# chain - optional - default is "mainnet"/"ethereum" 
# user-defined pool name and symbol - optional (defaults for either if not provided ONLY IF coin names are known - we know coin names either from coin addresses or user supply)
# coins - optional
    # list of addresses of existing tokens (take note of the order) - optional
        # optional since protocols may want to add their non-existent tokens (or new tokens with no pricing data/ liquidity for price reference)
        # no support for erc4626, custom oracle, rebasing, etc. tokens
    # list of usd prices - optional param (but no default value)
        # default network call being curve prices will suffice for coins that are in Curve's system (if not supplied by user)
        # consider switching to coingecko if curve prices fails - if both fail (prices not provided by user but addresses are), raise network exception
        # if no coin addresses and no usd prices and no pool address, raise exception
    # precision - optional param inside coins dict (if neither precisions nor addresses are provided, default value is 18 for all)
        # get from curve prices
# basepool - optional addr - format properly in to_metadata?
# start timestamp - optional (default is now - 60 days)
# .gin file data type: dict with "preset_name" as the unique trait
# function input type: dict of 1 of 3 types
# put function here to make simmarketconfigs having preset dicts reusable
# can keep CurvePreset around though, just to keep track of the preset names (don't give to SimMarketConfig)

# Note: timestamp and chain are already given default values in _c()
# (online call) (existing pool) - tier 1 
    # from_address(address, chain, end_ts=timestamp) (get_pool_data if doesn't work)
    # ignore everything else
    # apply preset params to curvesim_dict["params"] - however the unfilled (None) ones from this file can be ignored
    # apply tvl? - curvesim_dict["reserves"] overwrite?
# (online call) (existing coins, pool maybe nonexistent) - tier 2
    # if basepool, only accept 1 coin in coins (other is lp token of basepool) IF STABLESWAP PRESET
        # fetch whole curvesim dict at timestamp for the basepool from curve_prices
    # fetch coin prices and names, precisions at timestamp from coins[addresses] - use curve prices for coins in Curve's system, coingecko (or etherscan?) for when curve prices fails
        # ignore coins[names, decimals, prices]
        # coins[addresses] and chain - if basepool applies, need lp token price from different curve prices endpoint?
    # calculate curvesim_dict["reserves"] based on tvl and above fetched coin info
    # use name and symbol in curvesim dict if included
    # construct curvesim dict from above and insert into it all params for preset
# (no call) (coins and pool nonexistent) - tier 3
    # construct default name and symbol from coins[names] (in order)
    # address can be None, chain as "mainnet" default or chain is fine
    # calculate curvesim_dict["reserves"] based on tvl and coins[prices] and coins[decimals] (if supplied)
    # ignore basepool
    # apply preset to curvesim_dict["params"], add timestamp to curvesim_dict
    # (unrelated) user needs to supply a CsvDataSource (or other type for ReferenceMkt) for the coins (prices for the whole sim); query by SimAsset (not necessarily OnChainAssetPair) base/quote symbols



# returns dict - just adds predefined pool params (and determines pool type) on top of user-supplied info
    # for every pool type, there are used params and unused params (ie unnecessary to python pool init) - fill params (both types) fully based on pool type

# inside .gin, the dict["preset"] should be mapped to a str, not a CurvePreset

# unfilled params
params_not_preset = {
    "stableswap": {
        "admin_fee": None,
        # curve.fi preset includes maExpTime, but our stableswap pool.py does not
    },

    "cryptoswap": {
        "price_scale": None,
        "price_oracle": None,
        "last_prices": None,
        "last_prices_timestamp": None,
        "admin_fee": None,
        "xcp_profit": None,
        "xcp_profit_a": None,
    },
}

# invariant type
preset_to_invariant = {
    "fiat redeemable stablecoins": "stableswap",
    "crypto collateralized stablecoins": "stableswap",
    "stableswap liquid restaking tokens": "stableswap",
    "crypto": "cryptoswap",
    "forex": "cryptoswap",
    "liquid staking derivatives": "cryptoswap",
    "cryptoswap liquid restaking tokens": "cryptoswap",
    "tricrypto": "cryptoswap",
    "three coin volatile": "cryptoswap",
}

# params
{
    "fiat redeemable stablecoins": {
        "pool_type": "factory",
        "params": {
            "A": 200,
            "fee": int(0.0004 * 10**10),
            "fee_mul": 2 * 10**10,
            "ma_exp_time": 600,
        }.update(params_not_preset[preset_to_invariant["fiat redeemable stablecoins"]]),
    },
    "crypto collateralized stablecoins": {
        "pool_type": "factory",
        "params": {
            "A": 100,
            "fee": int(0.0004 * 10**10),
            "fee_mul": 2 * 10**10,
            "ma_exp_time": 600,
        }.update(params_not_preset[preset_to_invariant["crypto collateralized stablecoins"]]),
    },
    "stableswap liquid restaking tokens": {
        "pool_type": "factory",
        "params": {
            "A": 500,
            "fee": int(0.0001 * 10**10),
            "fee_mul": 5 * 10**10,
            "ma_exp_time": 600,
        }.update(params_not_preset[preset_to_invariant["stableswap liquid restaking tokens"]]),
    },
    "crypto": {
        "pool_type": "factory_crypto",
        "params": {
            "A": 400000,
            "gamma": int(0.000145 * 10**18),
            "fee_gamma": int(0.00023 * 10**18),
            "mid_fee": int(0.0026 * 10**10),
            "out_fee": int(0.0045 * 10**10),
            "allowed_extra_profit": int(0.000002 * 10**18),
            "adjustment_step": int(0.000146 * 10**18),
            "ma_half_time": 600,
        }.update(params_not_preset[preset_to_invariant["crypto"]]),
    },
    "forex": {
        "pool_type": "factory_crypto",
        "params": {
            "A": 20000000,
            "gamma": int(0.001 * 10**18),
            "fee_gamma": int(0.005 * 10**18),
            "mid_fee": int(0.0005 * 10**10),
            "out_fee": int(0.0045 * 10**10),
            "allowed_extra_profit": int(0.00000001 * 10**18),
            "adjustment_step": int(0.0000055 * 10**18),
            "ma_half_time": 600,
        }.update(params_not_preset[preset_to_invariant["forex"]]),
    },
    "liquid staking derivatives": {
        "pool_type": "factory_crypto",
        "params": {
            "A": 40000000,
            "gamma": int(0.002 * 10**18),
            "fee_gamma": int(0.3 * 10**18),
            "mid_fee": int(0.0003 * 10**10),
            "out_fee": int(0.0045 * 10**10),
            "allowed_extra_profit": int(0.00000001 * 10**18),
            "adjustment_step": int(0.0000055 * 10**18),
            "ma_half_time": 600,
        }.update(params_not_preset[preset_to_invariant["liquid staking derivatives"]]),
    },
    "cryptoswap liquid restaking tokens": {
        "pool_type": "factory_crypto",
        "params": {
            "A": 20000000,
            "gamma": int(0.02 * 10**18),
            "fee_gamma": int(0.03 * 10**18),
            "mid_fee": int(0.00005 * 10**10),
            "out_fee": int(0.0008 * 10**10),
            "allowed_extra_profit": int(0.00000001 * 10**18),
            "adjustment_step": int(0.0000055 * 10**18),
            "ma_half_time": 600,
        }.update(params_not_preset[preset_to_invariant["cryptoswap liquid restaking tokens"]]),
    },
    "tricrypto": {
        "pool_type": "factory_tricrypto",
        "params": {
            "A": 540000,
            "gamma": int(0.0000805 * 10**18),
            "fee_gamma": int(0.0004 * 10**18),
            "mid_fee": int(0.0001 * 10**10),
            "out_fee": int(0.014 * 10**10),
            "allowed_extra_profit": int(0.0000000001 * 10**18),
            "adjustment_step": int(0.0000001 * 10**18),
            "ma_half_time": 600,
        }.update(params_not_preset[preset_to_invariant["tricrypto"]]),
    },
    "three coin volatile": {
        "pool_type": "factory_tricrypto",
        "params": {
            "A": 2700000,
            "gamma": int(0.0000013 * 10**18),
            "fee_gamma": int(0.00035 * 10**18),
            "mid_fee": int(0.0002999999 * 10**10),
            "out_fee": int(0.008 * 10**10),
            "allowed_extra_profit": int(0.0000001 * 10**18),
            "adjustment_step": int(0.0000001 * 10**18),
            "ma_half_time": 600,
        }.update(params_not_preset[preset_to_invariant["three coin volatile"]]),
    },
}


# how to figure which dict type is which, how will simcontext figure which is which?
# simcontext: compare keys with templates above (if dict), if poolmetadatainterface, you already know

# rethink location of this file: pool/sim_interface instead?