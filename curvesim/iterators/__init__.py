"""
Iterators for use in simulation runs.
These are input directly into :func:`.pipelines.templates.run_pipeline`,
along with a strategy that is run at each timestemp.

Iterators fall into two general categories:

    1. :mod:`.param_samplers`: Generate pool with updated parameters per tick.
    2. :mod:`.price_samplers`: Generate price, volume, and/or other time-series data per tick.
"""
