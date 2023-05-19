"""
Canonical source of truth for version info.

The version number should not be changed manually here.  Instead,
a tool such as `bump2version` should be used.
"""
__version__ = "0.4.0.a1"
# FIXME: this logic isn't quite correct here for pre-release versions
__version_info__ = tuple(
    int(num) if num.isdigit() else num for num in __version__.split(".")
)
