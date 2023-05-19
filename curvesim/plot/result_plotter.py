from abc import ABC, abstractmethod


class ResultPlotter(ABC):
    """
    Result plotter base class with required properties for any result plotter object.

    """

    def __init__(self, plot_data, plot_results, plot_summary):
        """
        Parameters
        ----------
        plot_data : callable
            A function that takes a :class:`.metrics.SimResults` object and plots the
            data returned by :func:`SimResults.data`.

        plot_results : callable
            A function that takes a :class:`.metrics.SimResults` object and plots the
            data returned by both :func:`SimResults.summary` and :func:`SimResults.data`

        plot_summary : callable
            A function that takes a :class:`.metrics.SimResults` object and plots the
            data returned by :func:`SimResults.summary`.
        """

        self.plot_data = plot_data
        self.plot_results = plot_results
        self.plot_summary = plot_summary

    def plot(self, results, summary=True, data=True, save_as=None):
        """
        Returns and optionally saves a plot of the results data.
        Used in :func:`.results.SimResults.plot`

        Parameters
        ----------
        summary : bool, default=True
            If true, includes summary data in the plot.

        data : bool, default=True
            If true, includes timeseries data in the plot.

        save_as : str, optional
            Path to save plot output to.


        Returns
        -------
        A chart object.

        """
        if summary and data:
            chart = self.plot_results(results)
        elif summary:
            chart = self.plot_summary(results)
        elif data:
            chart = self.plot_data(results)

        if save_as:
            self.save(chart, save_as)

        return chart

    @abstractmethod
    def save(self, chart, save_as):
        """
        Saves the chart output by the plot() method.

        Parameters
        ----------
        chart
            A chart object.

        save_as : str
            Path to save plot output to.
        """
        raise NotImplementedError
