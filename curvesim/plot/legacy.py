"""
Plotters to visualize simulation results.

This code is likely to be changed soon.
"""


import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
from matplotlib.lines import Line2D


def plotsims(
    *,
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
    _plotsims_page_1(
        A_list=A_list,
        ar=ar,
        bal=bal,
        depth=depth,
        volume=volume,
        err=err,
    )

    if saveas:
        plt.savefig(saveas + "_1.png")

    _plotsims_page_2(
        A_list=A_list,
        bal=bal,
        pool_value=pool_value,
        depth=depth,
        volume=volume,
        log_returns=log_returns,
        err=err,
    )

    if saveas:
        plt.savefig(saveas + "_2.png")

    if show:
        plt.show()


def _plotsims_page_1(
    *,
    A_list,
    ar,
    bal,
    depth,
    volume,
    err,
):
    colors = plt.cm.viridis(np.linspace(0, 1, len(A_list)))

    # Summary stats
    _, axs = plt.subplots(2, 3, constrained_layout=True, figsize=(8, 5))

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
    for c in colors:
        line = Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=c,
            markersize=10,
        )
        handles.append(line)

    axs[1, 2].legend(handles, A_list, title="Amplitude", ncol=2)
    axs[1, 2].axis("off")


def _plotsims_page_2(
    *,
    A_list,
    bal,
    pool_value,
    depth,
    volume,
    log_returns,
    err,
):
    colors = plt.cm.viridis(np.linspace(0, 1, len(A_list)))

    # Time-series Data
    _, axs = plt.subplots(3, 2, constrained_layout=True, figsize=(8, 5))

    # Pool value
    for i, color in enumerate(colors):
        axs[0, 0].plot(pool_value.iloc[i], color=color)

    axs[0, 0].set_ylabel("Pool Value")
    plt.setp(axs[0, 0].xaxis.get_majorticklabels(), rotation=40, ha="right")
    axs[0, 0].yaxis.get_major_formatter().set_useOffset(False)

    # Balance
    for i, color in enumerate(colors):
        axs[0, 1].plot(bal.iloc[i], color=color)

    axs[0, 1].set_ylabel("Pool Balance")
    plt.setp(axs[0, 1].xaxis.get_majorticklabels(), rotation=40, ha="right")

    # Volume
    for i, color in enumerate(colors):
        axs[1, 0].plot(volume.T.resample("1D").sum().T.iloc[i], color=color)

    axs[1, 0].set_ylabel("Daily Volume")
    plt.setp(axs[1, 0].xaxis.get_majorticklabels(), rotation=40, ha="right")

    # Depth
    for i, color in enumerate(colors):
        axs[1, 1].plot(depth.iloc[i], color=color)

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


def plotsimsfee(*, A_list, fee_list, ar, bal, depth, volume, show=True, saveas=False):
    """
    Plots 2D summary output of Asims when multiple fees are used

    """
    fig, axs = plt.subplots(2, 3, constrained_layout=True, figsize=(11, 5.5))
    fee_list_pct = np.array(fee_list) / 10**8

    def plot_subfigure(ax, im, title, xlabel, ylabel):
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_xticks(np.arange(len(fee_list)))
        ax.set_yticks(np.arange(len(A_list)))
        ax.set_xticklabels(fee_list_pct)
        ax.set_yticklabels(A_list)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=90)
        cbar = fig.colorbar(im, ax=ax)
        return cbar

    # Annualized Returns
    ax = axs[0, 0]
    im = ax.imshow(ar.unstack("fee") * 100, cmap="plasma")
    plot_subfigure(
        ax, im, title="Annualized Returns (%)", xlabel="Fee (%)", ylabel="Amplitude (A)"
    )

    # Volume
    ax = axs[1, 0]
    im = ax.imshow(volume.sum(axis=1).unstack("fee"), cmap="plasma")
    plot_subfigure(ax, im, title="Volume", xlabel="Fee (%)", ylabel="Amplitude (A)")

    # Median Depth
    ax = axs[0, 1]
    im = ax.imshow(depth.median(axis=1).unstack("fee"), cmap="plasma")
    cbar = plot_subfigure(
        ax,
        im,
        title="Median Liquidity Density",
        xlabel="Fee (%)",
        ylabel="Amplitude (A)",
    )
    cbar.ax.yaxis.set_major_formatter(mtick.PercentFormatter())

    # Minimum Depth
    ax = axs[1, 1]
    im = ax.imshow(depth.min(axis=1).unstack("fee"), cmap="plasma")
    cbar = plot_subfigure(
        ax,
        im,
        title="Minimum Liquidity Density",
        xlabel="Fee (%)",
        ylabel="Amplitude (A)",
    )
    cbar.ax.yaxis.set_major_formatter(mtick.PercentFormatter())

    # Median Balance
    ax = axs[0, 2]
    im = ax.imshow(bal.median(axis=1).unstack("fee"), cmap="plasma")
    plot_subfigure(
        ax, im, title="Median Balance", xlabel="Fee (%)", ylabel="Amplitude (A)"
    )

    # Minimum Balance
    ax = axs[1, 2]
    im = ax.imshow(bal.min(axis=1).unstack("fee"), cmap="plasma")
    plot_subfigure(
        ax, im, title="Minimum Balance", xlabel="Fee (%)", ylabel="Amplitude (A)"
    )

    if saveas:
        plt.savefig(saveas + ".png")

    if show:
        plt.show()
