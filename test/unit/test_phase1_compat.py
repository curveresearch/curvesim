from curvesim.network.curve_prices import _chain_from_alias
from curvesim.sim import _apply_compat_defaults
from curvesim.templates import DateTimeSequence


def test_curve_prices_chain_aliases():
    assert _chain_from_alias("mainnet") == "ethereum"
    assert _chain_from_alias("matic") == "polygon"
    assert _chain_from_alias("arbitrum") == "arbitrum"


def test_autosim_test_mode_restores_default_grid():
    kwargs = _apply_compat_defaults({"test": True})

    assert kwargs["A"] == [100, 1000]
    assert kwargs["fee"] == [3000000, 4000000]


def test_autosim_days_builds_time_sequence():
    kwargs = _apply_compat_defaults({"days": 2})

    time_sequence = kwargs["time_sequence"]
    assert isinstance(time_sequence, DateTimeSequence)
    assert len(time_sequence) == 48


def test_autosim_days_preserves_explicit_time_sequence():
    explicit_time_sequence = DateTimeSequence.from_range(
        start="2024-01-01 00:00:00+00:00",
        end="2024-01-01 02:00:00+00:00",
        freq="1h",
    )

    kwargs = _apply_compat_defaults(
        {"days": 2, "time_sequence": explicit_time_sequence}
    )

    assert kwargs["time_sequence"] is explicit_time_sequence
