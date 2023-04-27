from abc import abstractmethod, abstractproperty


class PoolMetaDataInterface:
    @abstractmethod
    def init_kwargs(self, balanced=True, balanced_base=True, normalize=True):
        raise NotImplementedError

    @abstractproperty
    def address(self):
        raise NotImplementedError

    @abstractproperty
    def chain(self):
        raise NotImplementedError

    @abstractproperty
    def pool_type(self):
        raise NotImplementedError

    @abstractproperty
    def sim_pool_type(self):
        raise NotImplementedError

    @abstractproperty
    def coins(self):
        raise NotImplementedError

    @abstractproperty
    def coin_names(self):
        raise NotImplementedError

    @abstractproperty
    def n(self):
        raise NotImplementedError


class PoolMetaDataBase(PoolMetaDataInterface):
    def __init__(self, metadata_dict, pool_type, sim_pool_type):
        self._dict = metadata_dict
        self._pool_type = pool_type
        self._sim_pool_type = sim_pool_type

    @property
    def address(self):
        return self._dict["address"]

    @property
    def chain(self):
        return self._dict["chain"]

    @property
    def pool_type(self):
        return self._pool_type

    @property
    def sim_pool_type(self):
        return self._sim_pool_type
