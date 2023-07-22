from abc import ABC, abstractmethod


class PoolMetaDataInterface(ABC):
    @abstractmethod
    def init_kwargs(self, balanced=True, balanced_base=True, normalize=True):
        """
        Returns a dictionary of kwargs used to initialize the pool.

        Returns
        -------
        dict
        """
        raise NotImplementedError

    @abstractmethod
    @property
    def address(self):
        """
        Returns the pool address.

        Returns
        -------
        str
        """
        raise NotImplementedError

    @abstractmethod
    @property
    def chain(self):
        """
        Returns the chain/layer 2 identifier.

        Returns
        -------
        str
        """
        raise NotImplementedError

    @abstractmethod
    @property
    def pool_type(self):
        """
        Returns the pool type.

        Returns
        -------
        Pool

        """
        raise NotImplementedError

    @abstractmethod
    @property
    def sim_pool_type(self):
        """
        Returns the pool type.

        Returns
        -------
        SimPool

        """
        raise NotImplementedError

    @abstractmethod
    @property
    def coins(self):
        """
        Returns coin addresses for the pool's holdings.

        For pools that are not on Ethereum mainnet, the address
        for the corresponding mainnet token is returned.

        For lending tokens (e.g., aTokens or cTokens), the
        address for the underlying token is returned.

        Returns
        -------
        list of strings
            coin addresses

        """
        raise NotImplementedError

    @abstractmethod
    @property
    def coin_names(self):
        """
        Returns coin names for the pool's holdings.

        For pools that are not on Ethereum mainnet, the name
        of the corresponding mainnet token is returned.

        For lending tokens (e.g., aTokens or cTokens), the
        name of the underlying token is returned.

        Returns
        -------
        list of strings
            coin names

        """
        raise NotImplementedError

    @abstractmethod
    @property
    def n(self):
        """
        Returns the number of token-types (e.g., DAI, USDC, USDT) in a pool.

        Returns
        -------
        int or list of ints
            Number of token-types.

            For metapools, a list [n_metapool, n_basepool] is returned.

            N_metapool includes the basepool LP token.

        """
        raise NotImplementedError


class PoolMetaDataBase(PoolMetaDataInterface, ABC):
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
