from altair import Scale, Chart, data_transformers

from curvesim.exceptions import PlotError
from .chart_properties import make_chart_kwargs
from .styles import STYLES


data_transformers.disable_max_rows()


def make_chart(config, x=None, y=None, color=None, **kwargs):
    title = config.get("title", "")

    try:
        style = config["style"]
    except KeyError as e:
        raise PlotError(f"No style found in {title} config.") from e

    try:
        style = STYLES[style]
    except KeyError as e:
        raise PlotError(f"Style {style} not found in plot.styles.") from e

    defaults = make_defaults(title, x, y, color)
    chart_kwargs = make_chart_kwargs(defaults, [style, config, kwargs])
    return Chart(**chart_kwargs).interactive()


def make_defaults(title, x, y, color):
    defaults = {
        "title": title,
        "encoding": {
            "x": {},
            "y": {"title": title},
            "color": {"scale": Scale(scheme="viridis")},
        },
    }

    for key, val in zip(["x", "y", "color"], [x, y, color]):
        if val:
            if isinstance(val, str):
                val = {"shorthand": val}

            elif not isinstance(val, dict):
                cap = key.capitalize()
                raise PlotError(
                    f"{key} must be a string (shorthand) or dict (alt.{cap} kwargs)."
                )

            for k, v in val.items():
                defaults["encoding"][key][k] = v

    return defaults
