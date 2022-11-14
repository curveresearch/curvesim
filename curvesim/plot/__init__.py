"""
Plotters to visualize simulation results.

This code is likely to be changed soon.
"""
__all__ = ["saveplots"]

import os

import matplotlib.pyplot as plt

from .legacy import plotsims, plotsimsfee


def saveplots(folder_name, A_list, fee_list, results):
    """
    Save charts generated from `autosim`.

    Parameters
    ----------
    folder_name: str
        name of folder in `results` to save charts to;
        will create if needed
    A_list: list of int
        list of Amplification (A) paramters
    fee_list: list of int
        list of fee parameters
    results: dict
        results dict from `autosim`
    """
    base_filepath = os.path.join("results", folder_name)
    os.makedirs(base_filepath, exist_ok=True)

    if len(fee_list) > 1:
        filepath = os.path.join(base_filepath, "summary")
        plotsimsfee(
            A_list=A_list,
            fee_list=fee_list,
            ar=results["ar"],
            bal=results["bal"],
            depth=results["depth"],
            volume=results["volume"],
            show=False,
            saveas=filepath,
        )

    for curr_fee in fee_list:
        filename = "fee_" + str(round(curr_fee) / 10**8)[2:].ljust(2, "0")
        filepath = os.path.join(base_filepath, filename)

        plotsims(
            A_list=A_list,
            ar=results["ar"].loc[(slice(None), curr_fee), :],
            bal=results["bal"].loc[(slice(None), curr_fee), :],
            pool_value=results["pool_value"].loc[(slice(None), curr_fee), :],
            depth=results["depth"].loc[(slice(None), curr_fee), :],
            volume=results["volume"].loc[(slice(None), curr_fee), :],
            log_returns=results["log_returns"].loc[(slice(None), curr_fee), :],
            err=results["err"].loc[(slice(None), curr_fee), :],
            show=False,
            saveas=filepath,
        )

        plt.close("all")
