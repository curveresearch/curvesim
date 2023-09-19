Added
-----

- Add type checks via mypy to the CI (#252).
- `StateLog` is derived from a `Log` interface class in-line
  with other "template" classes.  This also helps avoid
  circular dependencies.
