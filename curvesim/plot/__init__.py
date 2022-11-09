"""
Plotters to visualize simulation results.

This code is likely to be changed soon.
"""

import os

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
from matplotlib.lines import Line2D


def plotsims(
    A_list,
    ar,
    bal,
    pool_value,
    depth,
    volume,
    log_returns,
    err,
    show=True,
    saveas=False,
):
    """
    Plots output of Asims when only 1 fee is used

    """

    colors = plt.cm.viridis(np.linspace(0, 1, len(A_list)))

    # Summary stats
    fig, axs = plt.subplots(2, 3, constrained_layout=True, figsize=(8, 5))

    axs[0, 0].plot(ar.unstack(level=1) * 100, "k", zorder=1)
    axs[0, 0].scatter(A_list, ar * 100, c=colors, zorder=2)
    axs[0, 0].yaxis.set_major_formatter(mtick.PercentFormatter())
    axs[0, 0].set_xlabel("Amplitude (A)")
    axs[0, 0].set_ylabel("Annualized Returns")

    axs[0, 1].plot(A_list, np.median(depth, axis=1), "k", zorder=1, label="Med")
    axs[0, 1].plot(A_list, np.min(depth, axis=1), "k--", zorder=1, label="Min")
    axs[0, 1].scatter(A_list, np.median(depth, axis=1), c=colors, zorder=2)
    axs[0, 1].scatter(A_list, np.min(depth, axis=1), c=colors, zorder=2)
    axs[0, 1].set_xlabel("Amplitude (A)")
    axs[0, 1].set_ylabel("Liquidity Density")
    axs[0, 1].legend(loc="lower right")

    axs[0, 2].plot(A_list, bal.median(axis=1), "k", zorder=1, label="Med")
    axs[0, 2].plot(A_list, bal.min(axis=1), "k--", zorder=1, label="Min")
    axs[0, 2].scatter(A_list, bal.median(axis=1), c=colors, zorder=2)
    axs[0, 2].scatter(A_list, bal.min(axis=1), c=colors, zorder=2)
    axs[0, 2].set_ylim([0, 1])
    axs[0, 2].set_xlabel("Amplitude (A)")
    axs[0, 2].set_ylabel("Pool Balance")
    axs[0, 2].legend(loc="lower right")

    axs[1, 0].plot(A_list, volume.sum(axis=1) / 60, "k", zorder=1)
    axs[1, 0].scatter(A_list, volume.sum(axis=1) / 60, c=colors, zorder=2)
    axs[1, 0].set_xlabel("Amplitude (A)")
    axs[1, 0].set_ylabel("Daily Volume")

    axs[1, 1].plot(A_list, err.median(axis=1), "k", zorder=1)
    axs[1, 1].scatter(A_list, err.median(axis=1), c=colors, zorder=2)
    axs[1, 1].set_xlabel("Amplitude (A)")
    axs[1, 1].set_ylabel("Median Price Error")

    # Legend
    handles = []
    for i in range(len(colors)):
        handles.append(
            Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                markerfacecolor=colors[i],
                markersize=10,
            )
        )

    axs[1, 2].legend(handles, A_list, title="Amplitude", ncol=2)
    axs[1, 2].axis("off")

    if saveas:
        plt.savefig(saveas + "_1.png")

    # Time-series Data
    fig, axs = plt.subplots(3, 2, constrained_layout=True, figsize=(8, 5))

    # Pool value
    for i in range(len(colors)):
        axs[0, 0].plot(pool_value.iloc[i], color=colors[i])

    axs[0, 0].set_ylabel("Pool Value")
    plt.setp(axs[0, 0].xaxis.get_majorticklabels(), rotation=40, ha="right")
    axs[0, 0].yaxis.get_major_formatter().set_useOffset(False)

    # Balance
    for i in range(len(colors)):
        axs[0, 1].plot(bal.iloc[i], color=colors[i])

    axs[0, 1].set_ylabel("Pool Balance")
    plt.setp(axs[0, 1].xaxis.get_majorticklabels(), rotation=40, ha="right")

    # Volume
    for i in range(len(colors)):
        axs[1, 0].plot(volume.T.resample("1D").sum().T.iloc[i], color=colors[i])

    axs[1, 0].set_ylabel("Daily Volume")
    plt.setp(axs[1, 0].xaxis.get_majorticklabels(), rotation=40, ha="right")

    # Depth
    for i in range(len(colors)):
        axs[1, 1].plot(depth.iloc[i], color=colors[i])

    axs[1, 1].set_ylabel("Liquidity Density")
    plt.setp(axs[1, 1].xaxis.get_majorticklabels(), rotation=40, ha="right")

    # Distribution of log returns
    axs[2, 0].hist(log_returns.T, 30, histtype="step", color=colors)
    axs[2, 0].set_xlabel("Log Returns")
    axs[2, 0].set_ylabel("Frequency")

    # Price error
    axs[2, 1].hist(err.T, 30, histtype="step", color=colors)
    axs[2, 1].set_xlabel("Price Error")
    axs[2, 1].set_ylabel("Frequency")

    if saveas:
        plt.savefig(saveas + "_2.png")

    if show:
        plt.show()


def plotsimsfee(A_list, fee_list, ar, bal, depth, volume, err, show=True, saveas=False):
    """
    Plots 2D summary output of Asims when multiple fees are used

    """
    fig, axs = plt.subplots(2, 3, constrained_layout=True, figsize=(11, 5.5))
    fee_list_pct = np.array(fee_list) / 10**8

    # Annualized Returns
    im = axs[0, 0].imshow(ar.unstack("fee") * 100, cmap="plasma")
    axs[0, 0].set_title("Annualized Returns (%)")
    axs[0, 0].set_xlabel("Fee (%)")
    axs[0, 0].set_ylabel("Amplitude (A)")
    axs[0, 0].set_xticks(np.arange(len(fee_list)))
    axs[0, 0].set_yticks(np.arange(len(A_list)))
    axs[0, 0].set_xticklabels(fee_list_pct)
    axs[0, 0].set_yticklabels(A_list)
    plt.setp(axs[0, 0].xaxis.get_majorticklabels(), rotation=90)
    cbar = fig.colorbar(im, ax=axs[0, 0])

    # Volume
    im = axs[1, 0].imshow(volume.sum(axis=1).unstack("fee"), cmap="plasma")
    axs[1, 0].set_title("Volume")
    axs[1, 0].set_xlabel("Fee (%)")
    axs[1, 0].set_ylabel("Amplitude (A)")
    axs[1, 0].set_xticks(np.arange(len(fee_list)))
    axs[1, 0].set_yticks(np.arange(len(A_list)))
    axs[1, 0].set_xticklabels(fee_list_pct)
    axs[1, 0].set_yticklabels(A_list)
    plt.setp(axs[1, 0].xaxis.get_majorticklabels(), rotation=90)
    cbar = fig.colorbar(im, ax=axs[1, 0])

    # Median Depth
    im = axs[0, 1].imshow(depth.median(axis=1).unstack("fee"), cmap="plasma")
    axs[0, 1].set_title("Median Liquidity Density")
    axs[0, 1].set_xlabel("Fee (%)")
    axs[0, 1].set_ylabel("Amplitude (A)")
    axs[0, 1].set_xticks(np.arange(len(fee_list)))
    axs[0, 1].set_yticks(np.arange(len(A_list)))
    axs[0, 1].set_xticklabels(fee_list_pct)
    axs[0, 1].set_yticklabels(A_list)
    plt.setp(axs[0, 1].xaxis.get_majorticklabels(), rotation=90)
    cbar = fig.colorbar(im, ax=axs[0, 1])
    cbar.ax.yaxis.set_major_formatter(mtick.PercentFormatter())

    # Minimum Depth
    im = axs[1, 1].imshow(depth.min(axis=1).unstack("fee"), cmap="plasma")
    axs[1, 1].set_title("Minimum Liquidity Density")
    axs[1, 1].set_xlabel("Fee (%)")
    axs[1, 1].set_ylabel("Amplitude (A)")
    axs[1, 1].set_xticks(np.arange(len(fee_list)))
    axs[1, 1].set_yticks(np.arange(len(A_list)))
    axs[1, 1].set_xticklabels(fee_list_pct)
    axs[1, 1].set_yticklabels(A_list)
    plt.setp(axs[1, 1].xaxis.get_majorticklabels(), rotation=90)
    cbar = fig.colorbar(im, ax=axs[1, 1])
    cbar.ax.yaxis.set_major_formatter(mtick.PercentFormatter())

    # Median Balance
    im = axs[0, 2].imshow(bal.median(axis=1).unstack("fee"), cmap="plasma")
    axs[0, 2].set_title("Median Balance")
    axs[0, 2].set_xlabel("Fee (%)")
    axs[0, 2].set_ylabel("Amplitude (A)")
    axs[0, 2].set_xticks(np.arange(len(fee_list)))
    axs[0, 2].set_yticks(np.arange(len(A_list)))
    axs[0, 2].set_xticklabels(fee_list_pct)
    axs[0, 2].set_yticklabels(A_list)
    plt.setp(axs[0, 2].xaxis.get_majorticklabels(), rotation=90)
    cbar = fig.colorbar(im, ax=axs[0, 2])

    # Minimum Balance
    im = axs[1, 2].imshow(bal.min(axis=1).unstack("fee"), cmap="plasma")
    axs[1, 2].set_title("Minimum Balance")
    axs[1, 2].set_xlabel("Fee (%)")
    axs[1, 2].set_ylabel("Amplitude (A)")
    axs[1, 2].set_xticks(np.arange(len(fee_list)))
    axs[1, 2].set_yticks(np.arange(len(A_list)))
    axs[1, 2].set_xticklabels(fee_list_pct)
    axs[1, 2].set_yticklabels(A_list)
    plt.setp(axs[1, 2].xaxis.get_majorticklabels(), rotation=90)
    cbar = fig.colorbar(im, ax=axs[1, 2])

    if saveas:
        plt.savefig(saveas + ".png")

    if show:
        plt.show()


def saveplots(poolname, A_list, fee_list, results):
    if not os.path.exists("results/" + poolname):
        os.makedirs("results/" + poolname)

    if len(fee_list) > 1:
        plotsimsfee(
            A_list,
            fee_list,
            results["ar"],
            results["bal"],
            results["depth"],
            results["volume"],
            results["err"],
            show=False,
            saveas="results/" + poolname + "/summary",
        )

    for curr_fee in fee_list:
        filename = (
            "results/"
            + poolname
            + "/fee_"
            + str(round(curr_fee) / 10**8)[2:].ljust(2, "0")
        )

        plotsims(
            A_list,
            results["ar"].loc[(slice(None), curr_fee), :],
            results["bal"].loc[(slice(None), curr_fee), :],
            results["pool_value"].loc[(slice(None), curr_fee), :],
            results["depth"].loc[(slice(None), curr_fee), :],
            results["volume"].loc[(slice(None), curr_fee), :],
            results["log_returns"].loc[(slice(None), curr_fee), :],
            results["err"].loc[(slice(None), curr_fee), :],
            show=False,
            saveas=filename,
        )

        plt.close("all")
