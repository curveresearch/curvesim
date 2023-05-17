from abc import ABC, abstractmethod


class ResultPlotter(ABC):
    def __init__(self, plot_data, plot_results, plot_summary):
        self.plot_data = plot_data
        self.plot_results = plot_results
        self.plot_summary = plot_summary

    def plot(self, results, summary=True, data=True, save_as=None):
        if summary and data:
            p = self.plot_results(results)
        elif summary:
            p = self.plot_summary(results)
        elif data:
            p = self.plot_data(results)

        if save_as:
            self.save(p, save_as)

        return p

    @abstractmethod
    def save(self, plot, save_as):
        raise NotImplementedError
