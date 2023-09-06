.. A new scriv changelog fragment.
..
.. Uncomment the header that is right (remove the leading dots).
..
.. Removed
.. -------
..
.. - A bullet item for the Removed category.
..
Added
-----

- Utils now has get_event_loop to access the event loop, which deprecates asyncio.get_event_loop.

Changed
-------

- In curvesim.network.nomics, curvesim.network.utils, and curvesim.pool_data.queries, all instances of
  asyncio.get_event_loop were replaced with get_event_loop imported from curvesim.utils.

- Updated deprecated license_file parameter to license_files in setup.cfg.

.. Deprecated
.. ----------
..
.. - A bullet item for the Deprecated category.
..
.. Fixed
.. -----
..
.. - A bullet item for the Fixed category.
..
.. Security
.. --------
..
.. - A bullet item for the Security category.
..
