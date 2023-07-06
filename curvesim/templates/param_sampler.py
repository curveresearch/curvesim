from abc import ABC, abstractmethod
from copy import deepcopy

from curvesim.logging import get_logger

logger = get_logger(__name__)


class ParameterSampler(ABC):
    """
    An iterator that yields pools with different parameter settings.
    """

    @abstractmethod
    def __iter__(self):
        """
        Yields
        -------
        pool : pool object
            A pool object with the current variable parameters set.

        params : dict
            A dictionary of the pool parameters set on this iteration.

        """
        raise NotImplementedError

    @abstractmethod
    def set_attributes(self, pool, attribute_dict):
        """
        Sets attributes on a pool.

        Parameters
        ----------
        pool : :class:`~curvesim.templates.SimPool`
            The pool object to be modified.

        attribute_dict : dict
            A dict mapping attribute names to values.
        """
        raise NotImplementedError


class SequentialParameterSampler(ParameterSampler):
    def __init__(self, pool, variable_params, fixed_params=None):
        """
        Parameters
        ----------
        pool : pool object
            The "template" pool that will have its parameters modified.

        variable_params: dict
            Pool parameters to vary across simulations.

            Keys: pool parameters, Values: iterable of values

            For metapools, using the (see :class:`MetaPoolAttributesMixin`) allows
            basepool attributes to be referenced by appending "_base" to a parameter
            name.

            Example
            -------
            .. code-block ::

                {"A": [100, 1000], "fee_base": [10**6, 4*10**6]}

        fixed_params : dict, optional
            Pool parameters set before all simulations.

            Keys: pool parameters, Values: single values

        """
        self.pool_template = deepcopy(pool)
        self.set_attributes(self.pool_template, fixed_params)
        self.parameter_sequence = self.make_parameter_sequence(variable_params)

    def __iter__(self):
        """
        Yields
        -------
        pool : pool object
            A pool object with the current variable parameters set.

        params : dict
            A dictionary of the pool parameters set on this iteration.

        """
        for params in self.parameter_sequence:
            pool = deepcopy(self.pool_template)
            self.set_attributes(pool, params)
            yield pool, params

    @abstractmethod
    def make_parameter_sequence(self, variable_params):
        """
        Returns a list of dicts defining the parameters to be set on each iteration.

        Parameters
        ----------
        variable_params
            Pool parameters to vary across simulations. Typically a dict.

        Returns
        -------
        List(dict)
            A list of dicts defining the parameters for each iteration.
        """
        return NotImplementedError

    @abstractmethod
    def set_attributes(self, pool, attribute_dict):
        """
        Sets attributes on a pool.

        Parameters
        ----------
        pool : :class:`~curvesim.templates.SimPool`
            The pool object to be modified.

        attribute_dict : dict
            A dict mapping attribute names to values.
        """
        raise NotImplementedError


class DynamicParameterSampler(ParameterSampler):
    def __init__(self):
        raise NotImplementedError
