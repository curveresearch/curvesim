__version__ = "0.3.0.a1"
__version_info__ = tuple(
    int(num) if num.isdigit() else num for num in __version__.split(".")
)
