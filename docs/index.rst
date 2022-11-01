.. curvesim documentation master file, created by
   sphinx-quickstart on Mon Oct 31 11:58:53 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Curvesim: Python Simulator for Curve Pools
==========================================

Release v\ |version|. (:ref:`Installation <install>`)

.. toctree::
   :maxdepth: 2
   :caption: Contents:

--------------------------

Pythonic interaction with Curve pool objects::

    >>> import curvesim

    >>> pool = curvesim.pool.get("3CRV")
    >>> pool.D()
    767840998051375021210088898

    >>> dx = 12345 * 10**6
    >>> pool.exchange(1, 2, dx)
    (12343765500, 1234499)

Arbitrage simulations to see results of varying fee and amplification (A) parameters::

    >>> import curvesim
    >>> curvesim.autosim("3CRV", A=[50, 75, 100, 150, 200])


Features
--------

Curvesim lets you...


User Guide
-----------

.. toctree::
   :maxdepth: 2

   install
   quickstart


API documentation
-----------------

.. toctree::
   :maxdepth: 2

   api


Indices and tables
-------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Contribute
----------

- Issue Tracker: github.com/$project/$project/issues
- Source Code: github.com/$project/$project

Support
-------

If you are having issues, please let us know.
We have a mailing list located at: project@google-groups.com

License
-------

The project is licensed under the BSD license.
