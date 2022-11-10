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
    >>> res = curvesim.autosim("3CRV", A=[75, 100, 150])
    Fetching CoinGecko price data...
    Fetching historical volume...
    Volume Multipliers:
    2.435631111781869e-05
    [3Crv] Simulating with {'A': 150}
    [3Crv] Simulating with {'A': 100}
    [3Crv] Simulating with {'A': 75}
    >>> res['pool_value']
         2022-09-01 23:30:00+00:00  ...  2022-11-01 23:30:00+00:00
    A                               ...
    75                7.922430e+08  ...               7.925223e+08
    100               7.922430e+08  ...               7.925253e+08
    150               7.922430e+08  ...               7.925288e+08

    [3 rows x 1465 columns]


Charts of the results are saved to the ``results`` folder.


Features
--------

Curvesim lets you:

* Simulate interactions with Curve pools in Python
* Analyze the effects of parameter changes on pool performance
* Develop custom simulation pipelines for pool optimization


User Guide
-----------

.. toctree::
   :maxdepth: 2

   install
   quickstart
   advanced


Recent Changes / Announcements
--------------------------------
.. toctree::
   :maxdepth: 1

   updates


API documentation
-----------------

.. toctree::
   :maxdepth: 2

   api


Contribute
----------

- Issue Tracker: github.com/curveresearch/curvesim/issues
- Source Code: github.com/curveresearch/curvesim

Support
-------

If you are having issues, please let us know.

Discord:


License
-------

Portions of the codebase are authorized derivatives of code owned by Curve.fi (Swiss Stake GbmH).  These are the vyper snippets used for testing (`test/fixtures/curve`) and the python code derived from them (`curvesim/pool/stableswap`); there are copyright notices placed appropriately.  The rest of the codebase has an MIT license.
