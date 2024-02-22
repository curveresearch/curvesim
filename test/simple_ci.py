"""
Test the entire sim pipeline code end-to-end, starting with pulling data
from the price provider (Coingecko) and the Curve subgraph.
"""
import argparse
import os
import pickle
import platform

import numpy as np
import pandas as pd

from curvesim.pipelines.simple import pipeline as simple_pipeline
from curvesim.templates import DateTimeSequence

TEST_PARAMS = {"A": [100, 1000], "fee": [3000000, 4000000]}
TEST_CRYPTO_PARAMS = {
    "A": [270000, 2700000],
    "gamma": [1300000000000, 13000000000],
    "fee_gamma": [500000000000000, 50000000000000],
    "out_fee": [80000000, 800000000],
}

pools = [
    # 3CRV
    {
        "address": "0xbebc44782c7db0a1a60cb6fe97d0b483032ff1c7",
        "params": TEST_PARAMS,
    },
    # aCRV
    {
        "address": "0xdebf20617708857ebe4f679508e7b7863a8a8eee",
        "params": TEST_PARAMS,
    },
    # # frax3CRV"
    {
        "address": "0xd632f22692fac7611d2aa1c0d552930d43caed3b",
        "params": TEST_PARAMS,
    },
    # triCRV
    {
        "address": "0x4ebdf703948ddcea3b11f675b4d1fba9d2414a14",
        "params": TEST_CRYPTO_PARAMS,
    },
]


def main(generate=False, ncpu=None):
    """
    Run the simple pipeline across the given pools, pulling pool and
    market data using the specified timestamp.

    Use `generate` to create and pickle the test data for comparison
    with the output of future code changes.

    Setting `ncpu` to 1 is useful for debugging and profiling.
    """

    data_dir = os.path.join("test", "data")

    test_functions = {
        "summary": summary,
        "per_run": per_run,
        "per_trade": per_trade,
    }

    for pool in pools:
        pool_address = pool["address"]
        pool_ts = 1707868800
        time_sequence = DateTimeSequence.from_range(
            end=pool_ts * 1e9, freq="1h", periods=1440
        )
        params = pool["params"]
        env = pool.get("env", "prod")

        results = simple_pipeline(
            pool_address,
            chain="mainnet",
            variable_params=params,
            time_sequence=time_sequence,
            pool_ts=pool_ts,
            ncpu=ncpu,
            env=env,
        )

        sim_data = {
            "per_run": results.data_per_run,
            "per_trade": results.data(),
            "summary": results.summary(),
        }

        for key in test_functions:
            f_name = os.path.join(
                data_dir, f"{pool_address.lower()}-simple_results_{key}.pickle"
            )

            if generate:
                with open(f_name, "wb") as f:
                    pickle.dump(sim_data[key], f)

            else:
                stored_data = pd.read_pickle(f_name)
                test_functions[key](sim_data[key], stored_data)


def per_run(sim, stored):
    print("Testing per-run data...")

    # Compare metric columns
    compare_metrics(sim.columns, stored.columns)
    sim = sim[stored.columns]

    # Compare runs
    sim_runs = list(sim.index)
    stored_runs = list(stored.index)
    assert (
        sim_runs == stored_runs
    ), "Simulation runs don't match between stored and tested data."

    # Test appropriate equality
    are_equal = sim.drop(["D"], axis=1) == stored.drop(["D"], axis=1)
    d_close = np.isclose(sim["D"], stored["D"], rtol=1e-2)

    # Feedback
    if not are_equal.all(axis=None):
        print("Per-run data: Equality Test for `A` and `fee`")
        print(are_equal)
        raise AssertionError("Equality test for `A` and `fee` failed.")
    if not all(d_close):
        print("Per-run data: Equality Test for `D`")
        print(d_close)
        raise AssertionError("Equality test for `D` failed.")

    print("Equality test passed.")


def per_trade(sim, stored, threshold=0.9):
    print("Testing per-trade data...")

    # Currently the CI fails on comparing `price_error`
    # between data generated on Ubuntu versus other
    # OSes.
    if platform.system() in ["Windows", "Darwin"]:
        sim = sim.drop(columns=["price_error"])
        stored = stored.drop(columns=["price_error"])
    # Compare metric columns
    compare_metrics(sim.columns, stored.columns)
    sim = sim[stored.columns]

    # Compare runs
    sim_runs = list(sim["run"].unique())
    stored_runs = list(stored["run"].unique())
    assert (
        sim_runs == stored_runs
    ), "Simulation runs don't match between stored and tested data."

    # Compute R-squared
    R2 = []
    for run in stored_runs:
        _sim = sim[sim["run"] == run].set_index("timestamp").drop("run", axis=1)
        _stored = (
            stored[stored["run"] == run].set_index("timestamp").drop("run", axis=1)
        )
        assert (
            _sim.shape == _stored.shape
        ), f"Per trade data, run {run}: data shape mismatch"

        R2.append(compute_R2(_sim.resample("1D").mean(), _stored.resample("1D").mean()))

    R2 = pd.DataFrame(R2).T

    # Feedback
    if not (R2 >= threshold).all(axis=None):
        print(R2)
        raise AssertionError(f"R-squared test failed. (Threshold: {threshold})")

    print(R2)
    print(f"R-squared test passed. (Threshold: {threshold}).")


def summary(sim, stored, threshold=0.99):
    print("Testing summary data...")

    # Compare metric columns
    compare_metrics(sim.columns, stored.columns)
    sim = sim[stored.columns]

    # Compare runs
    sim_runs = list(sim.index)
    stored_runs = list(stored.index)
    assert (
        sim_runs == stored_runs
    ), "Simulation runs don't match between stored and tested data."

    # Compute R-squared
    R2 = compute_R2(sim, stored)

    # Feedback
    if not (R2 >= threshold).all(axis=None):
        print(R2)
        raise AssertionError(f"R-squared test failed. (Threshold: {threshold})")

    print(R2)
    print(f"R-squared test passed. (Threshold: {threshold}).")


def compare_metrics(test, reference):
    extra, missing = compare_elements(test, reference)
    assert not missing, f"Metrics missing from simulation results: {missing}"

    if extra:
        print("WARNING: extra untested metrics in simulation results:", extra)


def compare_elements(test, reference):
    extra = [el for el in test if el not in reference]
    missing = [el for el in reference if el not in test]
    return extra, missing


def compute_R2(sim, stored):
    MSE = ((sim - stored) ** 2).sum()
    total_variance = stored.var(ddof=0)
    total_variance = total_variance.replace(0, 1)
    return 1 - MSE / total_variance


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Simple CI Test",
        description="Test end-to-end by running the simple pipeline across multiple pool types",
    )
    parser.add_argument(
        "-g",
        "--generate",
        action="store_true",
        help="Generate pickled test data",
    )
    parser.add_argument(
        "-n",
        "--ncpu",
        type=int,
        help="Number of cores to use; use 1 for debugging/profiling",
    )
    args = parser.parse_args()
    main(args.generate, args.ncpu)
