from altair import Tooltip


def make_tooltip(encoding, metric_axis, factors, prefix=None):
    tooltip = []
    if "timestamp" in encoding["x"]["shorthand"]:
        tooltip.append(Tooltip(encoding["x"]["shorthand"], title="Time"))

    title = encoding[metric_axis]["title"]
    if prefix:
        title = f"{prefix} {title}"

    tooltip.append(Tooltip(encoding[metric_axis]["shorthand"], title=title))

    return tooltip + factors
