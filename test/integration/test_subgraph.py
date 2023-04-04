import pytest

from curvesim.exceptions import SubgraphError
from curvesim.network.subgraph import _volume, pool_snapshot
from curvesim.network.utils import sync

ZERO_ADDRESS = "0x" + "00" * 20


def test_convex_subgraph_volume_query():
    """Test the volume query."""

    chain = "mainnet"
    address = "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"
    _volume_sync = sync(_volume)

    volumes = _volume_sync(ZERO_ADDRESS, chain, days=2)
    assert len(volumes) == 0

    volumes = _volume_sync(address, chain, days=2)
    assert len(volumes) == 2


def test_convex_subgraph_pool_snapshot_query():
    """Test the pool snapshot query."""

    chain = "mainnet"
    address = "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"
    address = "0x4e43151b78b5fbb16298C1161fcbF7531d5F8D93"
    _snapshot_sync = sync(pool_snapshot)

    with pytest.raises(SubgraphError):
        _snapshot_sync(ZERO_ADDRESS, chain)

    snapshot = _snapshot_sync(address, chain)
    assert snapshot["address"] == address
    assert snapshot["chain"] == chain

    print(snapshot)
