from abc import abstractmethod
from itertools import product

from curvesim.templates import SequentialParameterSampler
from .mixins import (
    PoolAttributeMixin,
    MetaPoolAttributeMixin,
    CurvePoolMixin,
    CurveCryptoPoolMixin,
)


class GridBase(SequentialParameterSampler):
    """
    Iterates over a "grid" of all possible combinations of the input parameters.
    """

    def make_parameter_sequence(self, variable_params):
        """
        Returns a list of dicts for each possible combination of the input parameters.

        Parameters
        ----------
        variable_params: dict
            Pool parameters to vary across simulations.

            Keys: pool parameters, Values: iterable of values

        Returns
        -------
        List(dict)
            A list of dicts defining the parameters for each iteration.
        """

        keys, values = zip(*variable_params.items())

        sequence = []
        for instance in product(*values):
            sequence.append(dict(zip(keys, instance)))

        return sequence

    @abstractmethod
    def set_attributes(self, pool, attribute_dict):
        """
        Sets the pool attributes defined in attribute_dict.

        Should support setting parameters with setattr(pool) and/or specialized setters
        defined in the attribute_setters property.
        """
        raise NotImplementedError

    @property
    def attribute_setters(self):
        """
        Returns a dict mapping attributes to a setter function.

        Used to set attributes that require more computation than simple setattr().
        """
        return {}


class CurvePoolGrid(PoolAttributeMixin, CurvePoolMixin, GridBase):
    pass


class CurveMetaPoolGrid(MetaPoolAttributeMixin, CurvePoolMixin, GridBase):
    pass


class CurveCryptoPoolGrid(PoolAttributeMixin, CurveCryptoPoolMixin, GridBase):
    pass
