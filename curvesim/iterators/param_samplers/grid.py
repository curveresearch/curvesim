from itertools import product

from curvesim.templates import SequentialParameterSampler
from .pool_mixins import CurvePoolMixin, CurveMetaPoolMixin, CurveCryptoPoolMixin


class Grid(SequentialParameterSampler):
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
        self._validate_attributes(self.pool_template, keys)

        sequence = []
        for vals in product(*values):
            params = dict(zip(keys, vals))
            sequence.append(params)

        return sequence


class CurvePoolGrid(CurvePoolMixin, Grid):
    """
    :class:`Grid` parameter sampler specialized for Curve pools.
    """

    pass


class CurveMetaPoolGrid(CurveMetaPoolMixin, Grid):
    """
    :class:`Grid` parameter sampler specialized for Curve meta-pools.
    """

    pass


class CurveCryptoPoolGrid(CurveCryptoPoolMixin, Grid):
    """
    :class:`Grid` parameter sampler specialized for Curve crypto pools.
    """

    pass
