from pandas import Grouper, Series, concat

from curvesim.exceptions import PlotError


def preprocess_data(data, config, factors, downsample=False):
    if downsample:
        return downsample_data(data, config, factors)
    else:
        return {"main": data.round(6)}


def downsample_data(data, config, factors):
    data_out = {}
    resample = {"run": "last"}
    for metric, cfg in config.items():
        rule = cfg.get("resample")

        if rule:
            resample[metric] = rule

        elif rule is False:
            data_out[metric] = data.pop(metric)

        elif cfg["style"].startswith("histogram"):
            d = concat([data[factors], data.pop(metric)], axis=1)
            data_out[metric] = to_histograms(d, factors)

        else:
            raise PlotError(f"No resample strategy found in {metric} config.")

    data_out["main"] = resample_data(data, factors, resample)
    return data_out


def resample_data(data, factors, fns):
    groups = factors + [Grouper(freq="1D", key="timestamp")]
    resampled = data.groupby(groups).agg(fns).round(6)
    return resampled.reset_index()


def to_histograms(data, factors):
    return data.groupby(factors).apply(make_histogram).reset_index()


def make_histogram(data, bins=500):
    metric = data.iloc[:, -1]
    minimum = Series(0, index=[metric.min()])

    hist = metric.value_counts(bins=bins, sort=False, normalize=True)
    hist.index = hist.index.right
    hist = concat([minimum, hist])
    hist.index.name, hist.name = metric.name, "frequency"
    return hist.round(6)
