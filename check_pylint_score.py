#!/usr/bin/env python3
# pylint: disable=redefined-outer-name
"""
Linting script that

- sets up the call args for pylint, including all the directories
- exits with failure if pylint finds any error (or fatal)
- exits with failure if pylint score is below THRESHOLD

This script is used locally via `make lint` and used in
the CI build.
"""

import sys

from pylint import lint

THRESHOLD = 9.4

# ANSI escape codes
BOLD = "\033[1m"
RESET = "\033[0m"
REVERSE = "\033[7m"
RED = "\033[00;31m"

FAILED_CHECK_MSG = f"{BOLD}pylint{RESET}: {RED}FAILED{RESET} checks"


def is_fatal_or_error(linter):
    """True if exit code contains fatal/error, False otherwise."""
    # bit-ORed exit code
    exit_code = linter.msg_status
    # last bit is FATAL, next bit is ERROR
    return exit_code & 0b11


class MissingScoreError(RuntimeError):
    """Pylint score is missing"""


class SysArgError(RuntimeError):
    """Incorrect or missing sys arg values"""


def get_score(linter):
    """Return Pylint score"""
    try:
        return linter.stats.global_note
    except KeyError:
        # score is missing if no lines of code checked
        raise MissingScoreError()


def score_fails_threshold(linter):
    """True if score is below threshold, False otherwise."""
    try:
        score = get_score(linter)
    except MissingScoreError:
        return False
    else:
        return score < THRESHOLD


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SysArgError("Need to provide at least one directory arg.")

    directories = sys.argv[1:]
    print(f"Running pylint on directories: {directories}\n")

    args = directories + ["--output-format=colorized"]
    linter = lint.Run(args, do_exit=False).linter

    exit_with_failure = False

    if is_fatal_or_error(linter):
        print("Pylint found errors.")
        exit_with_failure = True

    if score_fails_threshold(linter):
        score = get_score(linter)
        print("score is below required minimum: {} < {}.\n".format(score, THRESHOLD))
        exit_with_failure = True

    if exit_with_failure:
        print(FAILED_CHECK_MSG)
        sys.exit(1)

    score = get_score(linter)
    print(score)
