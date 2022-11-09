from copy import deepcopy
from itertools import product


class Grid:
    """
    Iterates over a "grid" of all possible combinations of the input parameters.
    """

    def __init__(self, pool, variable_params, fixed_params=None):
        """
        Parameters
        ----------
        pool : pool object
            The "template" pool that will have its parameters modified.

        variable_params: dict
            Pool parameters to vary across simulations.

            keys: pool parameters, values: iterables of ints

            Basepool parameters can be included with a "basepool" key.

            Example
            -------
            .. code-block ::

                variable_params = {"A": [100, 1000], "basepool": {fee: [10**6, 4*10**6]}}

        fixed_params : dict, optional
            Pool parameters set before all simulations.
            keys: pool parameters, values: ints

        """
        self.pool_template = pool
        self.set_attributes(self.pool_template, fixed_params)
        self.param_grid = self.param_product(variable_params)
        self.param_generator = iter(self.param_grid)

    def __iter__(self):
        return self

    def __next__(self):
        """
        Returns
        -------
        pool : pool object
            A pool object with the current variable parameters set.

        params : dict
            A dictionary of the pool parameters set on this iteration.

        """
        params = next(self.param_generator)
        pool = deepcopy(self.pool_template)
        self.set_attributes(pool, params)
        return pool, params

    def flat_grid(self):
        """
        Returns
        -------
        list of dicts
            A list of the parameters used in each iteration, flattened such
            that basepool parameters are named, e.g., A_base, fee_base, etc.

        """
        flat = self.param_grid.copy()
        for params in flat:
            basepool = params.pop("basepool", None)
            if basepool:
                for key, val in basepool.items():
                    params.update({key + "_base": val})

        return flat

    @staticmethod
    def param_product(p_dict):
        p_dict = p_dict.copy()
        basepool = p_dict.pop("basepool", None)

        keys = p_dict.keys()
        vals = p_dict.values()

        grid = []
        for instance in product(*vals):
            grid.append(dict(zip(keys, instance)))

        if basepool:
            base_keys = basepool.keys()
            base_vals = basepool.values()
            meta_grid = grid
            grid = []

            for meta_params in meta_grid:
                for instance in product(*base_vals):
                    base_params = dict(zip(base_keys, instance))
                    meta_params.update({"basepool": base_params})
                    grid.append(meta_params.copy())

        return grid

    @staticmethod
    def set_attributes(pool, attribute_dict):
        if attribute_dict is None:
            return

        for key, value in attribute_dict.items():
            if key == "basepool":
                items = attribute_dict["basepool"].items()
                for base_key, base_value in items:
                    if base_key == "D":
                        p = pool.basepool.p[:]
                        n = pool.basepool.n
                        D = base_value
                        x = [D // n * 10**18 // _p for _p in p]
                        pool.basepool.x = x

                    else:
                        setattr(pool.basepool, base_key, base_value)

            else:
                if key == "D":
                    p = getattr(pool, "rates", pool.p[:])
                    n = pool.n
                    D = value
                    x = [D // n * 10**18 // _p for _p in p]
                    pool.x = x

                else:
                    setattr(pool, key, value)
