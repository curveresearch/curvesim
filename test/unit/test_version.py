from curvesim.version import parse_version


def test_parse_version():
    """
    Check the version string gets correctly parsed to 'info' tuple.
    """
    version_tuple = parse_version("0.3.5")
    expected_result = (0, 3, 5, "release", 0)
    assert version_tuple == expected_result

    version_tuple = parse_version("0.3.5.release")
    expected_result = (0, 3, 5, "release", 0)
    assert version_tuple == expected_result

    version_tuple = parse_version("0.3.5.rc3")
    expected_result = (0, 3, 5, "rc", 3)
    assert version_tuple == expected_result

    version_tuple = parse_version("0.3.5.rc0")
    expected_result = (0, 3, 5, "rc", 0)
    assert version_tuple == expected_result

    version_tuple = parse_version("0.3.5.a12")
    expected_result = (0, 3, 5, "a", 12)
    assert version_tuple == expected_result
