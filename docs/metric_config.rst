Each metric's :code:`config` property specifies how to compute, summarize,
and/or plot recorded data. Users who intend to create their own metric objects
should familiarize themselves with the formatting specifications.

Config Specification
.....................

The general :code:`config` specification is:

::

    {
        "functions": {
            "metrics": function returning all sub_metrics,
            "summary": {
                "sub_metric1": str, list of str, or dict,
                "sub_metric2": str, list of str, or dict,
            },
        },
        "plot": {
            "metrics": {
                "sub_metric1": {
                    "title": str,
                    "style": str,
                    "resample": str,
                },

                "sub_metric2": {
                    "title": str,
                    "style": str,
                    "resample": str,
                },

            "summary":
                "sub_metric1": {
                    "title": str,
                    "style": str,
                },

                "sub_metric2": {
                    "title": str,
                    "style": str,
                },
    }


Pool Config Specification
.........................

For :class:`PoolMetric<curvesim.metrics.base.PoolMetric>` subclasses, a
:code:`pool_config` property must be specified to map pool-types to individual configs
in the above format:

::

    {
        PoolClass1: {
            "functions": ...
            "plot": ...
        },

        PoolClass2: {
            "functions": ...
            "plot": ...
        },
    }


Functions
.........

Functions used to compute metrics and/or summary statistics. Includes two sub-keys:

- :python:`config["functions"]["metrics"]`:
    A single function that computes all sub-metrics (in the same order specified
    throughout the config).

- :python:`config["functions"]["summary"]`:
    A dict mapping sub-metric names to functions for computing summary statistics. Functions can be specified using either:

    * a string referring to a pandas.DataFrame method (e.g., "sum", "mean", "median")
    * a sub-dict mapping a summary statistic's name to a function

For example, the :class:`ArbMetrics<curvesim.metrics.metrics.ArbMetrics>` config
specifies :code:`functions` as follows:

::

    "functions": {
                "metrics": self.compute_metrics,
                "summary": {
                    "arb_profit": "sum",
                    "pool_fees": "sum",
                    "pool_volume": "sum",
                    "price_error": "median",
                }
    }

When summary functions are specified as strings, the string is used to specify both
the function and the summary statistic's name in the results DataFrame. If a summary
function is specified with a dict, the key specifies the summary statistic's name,
and the value is the function to compute the statistic:

::

    "pool_value": {"annualized_returns": self._compute_annualized_returns}

Finally, multiple summary statistics can be specified for each sub-metric by using
either a list of strings or a dict with multiple items. For example:

::

    "pool_balance": ["median", "min"]

Or, if we sought to rename the summary statistics:

::

    "pool_balance": {"Median": "median", "Minimum": "min"}


Plot
....

Plotting specifications for metrics and/or summary statistics.

At minimum, the :code:`plot` key specifies a title, style, and (for sub-metrics, but
not summary statistics) a resampling function. Take for example this sub-section of
the :class:`ArbMetrics<curvesim.metrics.metrics.ArbMetrics>` config:

::

    "plot": {
            "metrics": {
                "arb_profit": {
                    "title": f"Daily Arbitrageur Profit (in {self.numeraire})",
                    "style": "time_series",
                    "resample": "sum",
                },
                "pool_fees": {
                    "title": f"Daily Pool Fees (in {self.numeraire})",
                    "style": "time_series",
                    "resample": "sum",
                },

            "summary": {
                "arb_profit": {
                    "title": f"Total Arbitrageur Profit (in {self.numeraire})",
                    "style": "point_line",
                },
                "pool_fees": {
                    "title": f"Total Pool Fees (in {self.numeraire})",
                    "style": "point_line",
                },

**Plot: Title**

The :code:`title` key specifies the title that will be shown above each plot. Because
:code:`config` is a property, we can use f-strings or other executable code to define
this or any other entry.

**Plot: Style**

The :code:`style` key indicates the plot style, as defined in
:mod:`plot.styles<curvesim.plot.styles>`.

Currently, the following styles are supported:

- *line* - a line plot
- *point_line* - a line plot with each individual point also marked
- *time_series* - a line plot with the x-axis set to the "timestamp" metric
- *histogram* - a normalized histogram with "Frequency" as the y-axis

Note that any of the style properties can be overriden by specifying additional properties in the plot config (see `Plot: Additional Properties` below). For histograms, the metric must be specified as the x-axis variable.

**Plot: Resample**

The :code:`resample` key defines what function to apply when the metric time-series are
downsampled before plotting. Because the full metric dataset can be very large,
we resample each metric to a sampling frequency of 1 day.

Any pandas function that returns a single value per time-bin is supported:
sum, mean, std, sem, max, min, median, first, or last.

See `pandas resampling docs <https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#resampling>`_ for more details.

Downsampling can be overriden by specifying :python:`"resample": False`.

**Plot: Additional Properties**

Each sub-metric or summary statistic's plot can be further customized by providing additional keys, which are passed as keyword arguments to `altair.Chart
<https://altair-viz.github.io/user_guide/generated/toplevel/altair.Chart.html>`_.

For example, in the :class:`ArbMetrics<curvesim.metrics.metrics.ArbMetrics>`
:python:`config["plot"]["metrics"]` entry, the encoding for the :code:`price_error` sub-metric is altered to specify the metric as the x-axis and truncate the x-axis scale:

::

    "price_error": {
        "title": "Price Error",
        "style": "histogram",
        "encoding": {
            "x": {
                "title": "Price Error (binned)",
                "shorthand": "price_error",
                "scale": Scale(domain=[0, 0.05], clamp=True),
            },
        },
    },


In the above example, the :code:`"encoding"` key would be passed to :python:`altair.Chart` as a keyword argument after the sub-dict :code:`"x"` was passed to :python:`altair.X`.
