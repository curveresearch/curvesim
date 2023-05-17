from altair import Axis, Scale

STYLES = {
    "line": {
        "mark": {"type": "line"},
        "encoding": {
            "x": {"scale": Scale(zero=False)},
            "y": {"scale": Scale(zero=False)},
        },
    },
    "point_line": {
        "mark": {"type": "line", "point": True},
        "encoding": {
            "x": {"scale": Scale(zero=False)},
            "y": {"scale": Scale(zero=False)},
        },
    },
    "time_series": {
        "mark": {"type": "line"},
        "encoding": {
            "x": {"title": None, "shorthand": "timestamp"},
            "y": {"scale": Scale(zero=False)},
        },
    },
    "histogram": {
        "mark": {"type": "line", "interpolate": "step-before"},
        "encoding": {
            "x": {"scale": Scale(zero=False)},
            "y": {
                "title": "Frequency",
                "shorthand": "frequency",
                "scale": Scale(zero=True),
                "axis": Axis(format="%"),
            },
        },
    },
}
