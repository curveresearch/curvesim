#!/usr/bin/env python3
"""
This script checks the coverage and checks it doesn't decrease.
"""

import os.path
import sys


def main():
    """exit with failure if coverage has decreased since last run"""
    try:
        coverage_score = int(sys.stdin.read())
    except ValueError:
        print("Bad value for coverage score.")
        sys.exit(1)

    filepath = "coverage_score.txt"
    if os.path.isfile(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                old_coverage_score = int(f.read())
            except ValueError:  # no int found
                print("Bad value for previous coverage score.")
                exit_status = 0
            else:
                exit_status = int(coverage_score < old_coverage_score)
                if exit_status:
                    print(
                        "Coverage decreased by {}%, from {}% to {}%".format(
                            old_coverage_score - coverage_score,
                            old_coverage_score,
                            coverage_score,
                        )
                    )
    else:
        # no old file found, so we can't compare. Assume this is ok
        print("No previous coverage score found.")
        exit_status = 0

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(str(coverage_score))

    sys.exit(exit_status)


if __name__ == "__main__":
    main()
