from altair import Tooltip


def make_tooltip(encoding, metric_axis, factors, prefix=None):
    """Makes a tooltip for a subplot."""
    tooltip = []

    x_shorthand = encoding["x"]["shorthand"]
    if isinstance(x_shorthand, str) and "timestamp" in x_shorthand:
        tooltip.append(Tooltip(x_shorthand, title="Time"))

    title = encoding[metric_axis]["title"]
    if prefix:
        title = f"{prefix} {title}"

    tooltip.append(Tooltip(encoding[metric_axis]["shorthand"], title=title))

    return tooltip + factors
