from math import comb

from curvesim.pool_data.queries.pool_volume import _get_pair_data


class DummyMetadata:
    def __init__(self, address, coin_names, coin_addresses, n, basepool_address=None):
        self.address = address
        self.coin_names = coin_names
        self.coins = coin_addresses
        self.n = n
        self._dict = {
            "basepool": {"address": basepool_address},
            "coins": coin_addresses,
        }


def make_dummy_metadata(n):
    if isinstance(n, list):
        n_total = sum(n) - 1
    else:
        n_total = n

    kwargs = {
        "address": "pool_address",
        "coin_names": ["SYM" + str(i) for i in range(n_total)],
        "coin_addresses": ["ADR" + str(i) for i in range(n_total)],
        "n": n,
        "basepool_address": "basepool_address",
    }

    return DummyMetadata(**kwargs), n_total


def test_get_pair_data():
    for n in range(2, 5):
        pool_metadata, n_total = make_dummy_metadata(n)
        pair_data = _get_pair_data(pool_metadata)
        pair_data = tuple(pair_data)
        pool_addresses, pair_addresses, pair_symbols = zip(*pair_data)

        # Ensure correct length
        assert len(pair_data) == comb(n_total, 2)

        # Ensure correct pool address
        assert pool_addresses == ("pool_address",) * comb(n_total, 2)

        # Ensure all pairs unique
        assert len(pair_addresses) == len(set(pair_addresses))  # all pairs unique
        assert len(pair_symbols) == len(set(pair_symbols))  # all pairs unique

        # Ensure all items present
        assert {x for pair in pair_addresses for x in pair} == set(pool_metadata.coins)
        assert {x for pair in pair_symbols for x in pair} == set(
            pool_metadata.coin_names
        )


def test_get_pair_data_metapool():
    n_list = [[n1, n2] for n1 in range(2, 4) for n2 in range(2, 5)]
    for n in n_list:
        pool_metadata, n_total = make_dummy_metadata(n)
        pair_data = _get_pair_data(pool_metadata)
        pool_addresses, pair_addresses, pair_symbols = zip(*pair_data)

        # Ensure correct length
        assert len(pair_data) == comb(n_total, 2)

        # Ensure correct pool addresses
        n_meta = n[0] - 1
        n_base = n[1]
        n_pairs_meta = comb(n_meta, 2) + n_meta * n_base
        n_pairs_base = comb(n_base, 2)
        assert (
            pool_addresses
            == ("pool_address",) * n_pairs_meta + ("basepool_address",) * n_pairs_base
        )

        # Ensure all pairs unique
        assert len(pair_addresses) == len(set(pair_addresses))  # all pairs unique
        assert len(pair_symbols) == len(set(pair_symbols))  # all pairs unique

        # Ensure all items present
        assert {x for pair in pair_addresses for x in pair} == set(pool_metadata.coins)
        assert {x for pair in pair_symbols for x in pair} == set(
            pool_metadata.coin_names
        )
