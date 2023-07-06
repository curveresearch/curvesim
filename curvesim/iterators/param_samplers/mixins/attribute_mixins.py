from abc import ABC, abstractmethod

from curvesim.exceptions import ParameterSamplerError


class AttributeMixin(ABC):
    """
    Defines the set_attributes method.
    """

    @abstractmethod
    def set_attributes(self, pool, attribute_dict):
        raise NotImplementedError

    def _set_attribute(self, pool, key, value):
        if key in self.attribute_setters:
            self.attribute_setters[key](pool, value)

        elif hasattr(pool, key):
            setattr(pool, key, value)

        else:
            pool_type = pool.__class__.__name__
            sampler_type = self.__class__.__name__

            raise ParameterSamplerError(
                f"'{pool_type}' has no attribute '{key}',"
                f"and '{key}' not found in '{sampler_type}.attribute_setters'."
            )


class PoolAttributeMixin(AttributeMixin):
    """
    Parameter sampler mixin used for any non-meta pool.
    Defines the set_attributes method.
    """

    def set_attributes(self, pool, attribute_dict):
        if attribute_dict is None:
            return

        for key, value in attribute_dict.items():
            self._set_attribute(pool, key, value)


class MetaPoolAttributeMixin(AttributeMixin):
    """
    Parameter sampler mixin used for any meta pool.
    Defines the set_attributes method.

    Allows setting parameters on pool.basepool by appending "_base" to parameter names.
    """

    def set_attributes(self, pool, attribute_dict):
        if attribute_dict is None:
            return

        for key, value in attribute_dict.items():
            if key.endswith("_base"):
                _pool = pool.basepool
                _key = key[:-5]

            else:
                _pool = pool
                _key = key

            self._set_attribute(_pool, _key, value)
