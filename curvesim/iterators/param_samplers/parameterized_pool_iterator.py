from abc import abstractmethod
from copy import deepcopy
from itertools import product

from curvesim.exceptions import ParameterSamplerError
from curvesim.pool.sim_interface import (
    SimCurveCryptoPool,
    SimCurveMetaPool,
    SimCurvePool,
    SimCurveRaiPool,
)
from curvesim.templates import ParameterSampler

from .pool_mixins import CurveCryptoPoolMixin, CurveMetaPoolMixin, CurvePoolMixin


class ParameterizedPoolIterator(ParameterSampler):
    """
    Iterates over pools with all possible combinations of the input parameters.
    """

    # pylint: disable-next=unused-argument
    def __new__(cls, pool, variable_params=None, fixed_params=None, pool_map=None):
        """
        Returns a pool-specific ParameterizedPoolIterator subclass.

        Parameters
        ----------
        pool_map : dict, optional
            A mapping between pool types and subclasses. Overrides default mapping.

        Returns
        -------
            :class:`.ParameterizedPoolIterator` subclass

        """
        pool_map = pool_map or DEFAULT_POOL_MAP

        if cls is not ParameterizedPoolIterator:
            return super().__new__(cls)

        try:
            pool_type = type(pool)
            subclass = pool_map[pool_type]

        except KeyError as e:
            pool_type_name = pool_type.__name__
            raise ParameterSamplerError(
                f"No subclass for pool type `{pool_type_name}` found in "
                "ParameterizedPoolIterator pool map."
            ) from e

        return super().__new__(subclass)

    # pylint: disable-next=unused-argument
    def __init__(self, pool, variable_params=None, fixed_params=None, pool_map=None):
        """
        Parameters
        ----------
        pool : :class:`~curvesim.templates.SimPool`
            The "template" pool that will have its parameters modified.

        variable_params: dict, optional
            Pool parameters to vary across simulations.

            Keys are parameter names and values are iterables of values. For metapools,
            basepool parameters can be referenced by appending "_base" to an attribute
            name.

            Example
            --------
            .. code-block ::

                {"A": [100, 1000], "fee_base": [10**6, 4*10**6]}

        fixed_params : dict, optional
            Pool parameters set before all simulations.

        pool_map : dict, optional
            See __new__ method.

        """
        self._validate_pool_type(pool)
        self.pool_template = deepcopy(pool)
        self.set_pool_attributes(self.pool_template, fixed_params)
        parameter_sequence = self.make_parameter_sequence(variable_params)
        self.parameter_sequence = parameter_sequence or [fixed_params]

    def __iter__(self):
        """
        Yields
        -------
        pool : :class:`~curvesim.templates.SimPool`
            A pool object with the current variable parameters set.

        params : dict
            A dictionary of the pool parameters set on this iteration.
        """
        for params in self.parameter_sequence:
            pool = deepcopy(self.pool_template)
            self.set_pool_attributes(pool, params)
            yield pool, params

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
        if not variable_params:
            return []

        keys, values = zip(*variable_params.items())
        self._validate_attributes(self.pool_template, keys)

        sequence = []
        for vals in product(*values):
            params = dict(zip(keys, vals))
            sequence.append(params)

        return sequence

    def _validate_pool_type(self, pool):
        """Validates that the input pool is an instance of self._pool_type."""
        if not isinstance(pool, self._pool_type):
            input_class = pool.__class__.__name__
            expected_class = self._pool_type.__name__
            self_class = self.__class__.__name__

            raise ParameterSamplerError(
                f"Parameter sampler '{self_class}' only supports pool type "
                f"'{expected_class}'; recieved '{input_class}'."
            )

    @property
    @abstractmethod
    def _pool_type(self):
        """The expected pool type for a ParameterizedPoolIterator subclass."""
        raise NotImplementedError


class ParameterizedCurvePoolIterator(CurvePoolMixin, ParameterizedPoolIterator):
    """
    :class:`ParameterizedPoolIterator` parameter sampler specialized
    for Curve pools.
    """


class ParameterizedCurveMetaPoolIterator(CurveMetaPoolMixin, ParameterizedPoolIterator):
    """
    :class:`ParameterizedPoolIterator` parameter sampler specialized
    for Curve meta-pools.
    """


class ParameterizedCurveCryptoPoolIterator(
    CurveCryptoPoolMixin, ParameterizedPoolIterator
):
    """
    :class:`ParameterizedPoolIterator` parameter sampler specialized
    for Curve crypto pools.
    """


DEFAULT_POOL_MAP = {
    SimCurvePool: ParameterizedCurvePoolIterator,
    SimCurveRaiPool: ParameterizedCurveMetaPoolIterator,
    SimCurveMetaPool: ParameterizedCurveMetaPoolIterator,
    SimCurveCryptoPool: ParameterizedCurveCryptoPoolIterator,
}
