"""
Parameter overrides for cases that need special handling.
"""
from copy import deepcopy

subgraph_overrides = {
    "pool_snapshot": {
        ("0xA5407eAE9Ba41422680e2e00537571bcC53efBfD", "mainnet"): {
            "pool_type": "REGISTRY_V1"
        }
    }
}


def override_subgraph_data(data, function_key, data_key):
    """
    Applies overrides to subgraph data.

    Parameters
    ----------
    data : dict
        The data to be potentially overriden.

    function_key : str
        The function to lookup overrides for (i.e., subgraph_overrides[function_key]).

    data_key :
        The key for the specific item to lookup overrides for
        (i.e., subgraph_overrides[function_key][data_key])

    Returns
    -------
    dict
        The input data with any overrides applied.

    """
    overrides = subgraph_overrides[function_key]

    if data_key in overrides:
        data = deepcopy(data)
        for key, val in overrides[data_key].items():
            data.update({key: val})

    return data
