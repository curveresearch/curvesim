from abc import ABC, abstractmethod

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

        self._validate_attributes(pool, attribute_dict)

        for attribute, value in attribute_dict.items():
            self._set_pool_attribute(pool, attribute, value)

    @property
    def setters(self):
        """
        A dict mapping attributes to setter functions.

        Used to set attributes that require more computation than simple setattr().
        Typically defined in pool-specific mixin. Defaults to empty dict.

        For metapools, basepool parameters can be referenced by appending "_base" to
        an attribute's name.

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

        For metapools, basepool parameters can be referenced by appending "_base" to
        an attribute's name.

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

        else:
            pool_attr = parse_pool_attribute(pool, attr)
            setattr(*pool_attr, value)

    def _validate_attributes(self, pool, attributes):
        """
        Raises error if attributes are not present in self.setters or pool attributes.

        Parameters
        ----------
        pool : :class:`~curvesim.templates.SimPool`
            The pool object to be modified.

        attributes : Iterable[str]
            Iterable of attribute names.

        Raises
        ------
        ParameterSamplerError

        """
        missing = []
        for attribute in attributes:
            pool_attr = parse_pool_attribute(pool, attribute)

            if attribute not in self.setters and not hasattr(*pool_attr):
                missing.append(attribute)

        if missing:
            pool_class = pool.__class__.__name__
            self_class = self.__class__.__name__

            raise ParameterSamplerError(
                f"Input parameters not found in '{self_class}.setters' "
                f"or '{pool_class}' attributes: {missing}"
            )


def parse_pool_attribute(pool, attribute):
    """
    Helper function to route "_base" attributes to basepool if necessary.
    """
    if attribute.endswith("_base"):

        if not hasattr(pool, "basepool"):
            pool_class = pool.__class__.__name__

            raise ParameterSamplerError(
                f"Could not set pool parameter '{attribute}'; "
                f"'{pool_class}' has no basepool."
            )

        return pool.basepool, attribute[:-5]

    return pool, attribute
