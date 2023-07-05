"""
Canonical source of truth for version info.

The version number should not be changed manually here.  Instead,
a tool such as `bump2version` should be used.
"""
import re

__version__ = "0.4.5"


def parse_version(version):
    """
    Return a lexicographically comparable version sequence.
    """
    match = re.match(r"(\d+)\.(\d+)\.(\d+)\.?([a-z]*)(\d*)", version)
    major, minor, patch, release, build = match.groups()

    return (
        int(major),
        int(minor),
        int(patch),
        release or "release",  # '' means 'release'
        int(build) if build else 0,
    )


__version_info__ = parse_version(__version__)


if __name__ == "__main__":
    print(parse_version("0.3.5"))  # (0, 3, 5, 'release', 0)
    print(parse_version("0.3.5.release"))  # (0, 3, 5, release, 0)
    print(parse_version("0.3.5.rc3"))  # (0, 3, 5, rc, 3)
    print(parse_version("0.3.5.rc0"))  # (0, 3, 5, rc, 0)
    print(parse_version("0.3.5.a12"))  # (0, 3, 5, a, 12)
