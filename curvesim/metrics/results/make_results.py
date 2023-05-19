from pandas import concat

from .sim_results import SimResults


def make_results(data_per_run, data_per_trade, summary_data, metrics):
    """Initializes a results object from the output of a simulation pipeline."""

    for run_n, data in enumerate(data_per_trade):  # add "run" column
        data.insert(0, "run", run_n)

    data_per_run = concat(data_per_run, ignore_index=True)
    data_per_trade = concat(data_per_trade, ignore_index=True)
    summary_data = concat(summary_data, ignore_index=True)

    factors = get_factors(data_per_run)
    plot_config = combine_plot_configs(metrics)

    return SimResults(data_per_run, data_per_trade, summary_data, factors, plot_config)


def combine_plot_configs(metrics):
    """Combines plot configs across all metrics."""

    metrics_config = {}
    summary_config = {}
    for metric in metrics:
        if metric.plot_config:
            metrics = metric.plot_config.get("metrics", {})
            summary = metric.plot_config.get("summary", {})
            metrics_config.update(metrics)
            summary_config.update(summary)
    return {"data": metrics_config, "summary": summary_config}


def get_factors(data_per_run):
    """Returns dict mapping variable parameters to their values."""

    factors = {}
    for parameter in data_per_run:
        unique_values = data_per_run[parameter].unique()
        if len(unique_values) > 1:
            factors[parameter] = list(unique_values)

    return factors
