from abc import ABC, abstractmethod
from copy import deepcopy

from curvesim.exceptions import ParameterSamplerError
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
        pool : :class:`~curvesim.templates.SimPool`
            A pool object with the current variable parameters set.

        params : dict
            A dictionary of the pool parameters set on the current iteration.

        """
        raise NotImplementedError

    def set_pool_attributes(self, pool, attribute_dict):
        """
        Sets the pool attributes defined in attribute_dict.

        Supports setting attributes with :python:`setattr(pool, key, value)` or
        specialized setters defined in the 'setters' property:
        :python:`self.setters[key](pool, value)`

        For metapools, basepool parameters can be referenced by appending "_base" to
        an attribute's name.

        Parameters
        ----------
        pool : :class:`~curvesim.templates.SimPool`
            The pool object to be modified.

        attribute_dict : dict
            A dict mapping attribute names to values.
        """

        if attribute_dict is None:
            return

        for attribute, value in attribute_dict.items():
            if attribute.endswith("_base"):
                args = (pool.basepool, attribute[:-5])

            else:
                args = (pool, attribute)

            self._set_pool_attribute(*args, value)

    @property
    def setters(self):
        """
        A dict mapping attributes to setter functions.

        Used to set attributes that require more computation than simple setattr().
        Typically defined in pool-specific mixin. Defaults to empty dict.

        Returns
        -------
        dict
        """
        return {}

    def _set_pool_attribute(self, pool, attr, value):
        """
        Sets a single pool attribute.

        Supports setting attributes with :python:`setattr(pool, attr, value)` or
        specialized setters defined in the 'setters' property:
        :python:`self.setters[attr](pool, value)`

        Parameters
        ----------
        pool : :class:`~curvesim.templates.SimPool`
            The pool object to be modified.

        attr : str
            The attribute to be set.

        value :
            The value to be set for the attribute.
        """

        if attr in self.setters:
            self.setters[attr](pool, value)

        elif hasattr(pool, attr):
            setattr(pool, attr, value)

        else:
            pool_class = pool.__class__.__name__
            sampler_class = self.__class__.__name__

            raise ParameterSamplerError(
                f"'{pool_class}' has no attribute '{attr}',"
                f"and '{attr}' not found in '{sampler_class}.setters'."
            )


class SequentialParameterSampler(ParameterSampler):
    """
    Parameter sampler that yields pools using a fixed sequence of parameters.
    """

    def __init__(self, pool, variable_params, fixed_params=None):
        """
        Parameters
        ----------
        pool : :class:`~curvesim.templates.SimPool`
            The "template" pool that will have its parameters modified.

        variable_params: dict
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

        """
        self.pool_template = deepcopy(pool)
        self.set_pool_attributes(self.pool_template, fixed_params)
        self.parameter_sequence = self.make_parameter_sequence(variable_params)

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


class AdaptiveParameterSampler(ParameterSampler):
    """
    Parameter sampler that selects parameters adaptively based on simulation results.
    """

    def __init__(self):
        raise NotImplementedError
