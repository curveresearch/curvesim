from copy import deepcopy
from itertools import product


class Grid:
    def __init__(self, pool, variable_params, fixed_params=None):
        self.pool_template = pool
        self.set_attributes(self.pool_template, fixed_params)
        self.param_grid = self.param_product(variable_params)
        self.param_generator = iter(self.param_grid)

    def __iter__(self):
        return self

    def __next__(self):
        params = next(self.param_generator)
        pool = deepcopy(self.pool_template)
        self.set_attributes(pool, params)
        return pool, params

    @staticmethod
    def param_product(p_dict):
        p_dict = p_dict.copy()

        basepool = None
        if "basepool" in p_dict.keys():
            basepool = p_dict.pop("basepool")

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
                    setattr(pool.basepool, base_key, base_value)

            else:
                setattr(pool, key, value)
