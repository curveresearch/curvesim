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

    >>> pool = curvesim.pool.get("0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7")
    >>> pool.D()
    767840998051375021210088898

    >>> dx = 12345 * 10**6
    >>> pool.exchange(1, 2, dx)
    (12343765500, 1234499)

Arbitrage simulations to see results of varying fee and amplification (A) parameters::

    >>> import curvesim
    >>> res = curvesim.autosim("0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7", A=[75, 100, 150])
    [INFO][18:07:40][curvesim.price_data.sources]-37676: Fetching CoinGecko price data...
    [INFO][18:07:41][curvesim.pool_data.cache]-37676: Fetching historical volume...
    [INFO][18:07:41][curvesim.network.subgraph]-37676: Volume end date: 2023-05-18 00:00:00+00:00
    [INFO][18:08:01][curvesim.pipelines.utils]-37676: Volume Multipliers: 3.18995731844421e-05
    [INFO][18:08:11][curvesim.pipelines.arbitrage]-37681: [3Crv] Simulating with {'A': 150}
    [INFO][18:08:11][curvesim.pipelines.arbitrage]-37679: [3Crv] Simulating with {'A': 75}
    [INFO][18:08:11][curvesim.pipelines.arbitrage]-37680: [3Crv] Simulating with {'A': 100}
    >>> res.summary()
    metric pool_value_virtual         pool_value pool_balance            ...    arb_profit      pool_fees   pool_volume price_error
    stat   annualized_returns annualized_returns       median       min  ...           sum            sum           sum      median
    0                0.004011           0.016755     0.978391  0.849874  ...  2.325945e+06  259281.790355  2.590492e+09    0.000755
    1                0.004195           0.016959     0.971582  0.819401  ...  2.433098e+06  271161.675686  2.709161e+09    0.000839
    2                0.004353           0.017136     0.958596  0.775227  ...  2.575127e+06  281329.583883  2.810715e+09    0.000933

    [3 rows x 10 columns]



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


API Documentation
-----------------

.. toctree::
   :maxdepth: 2

   api


Contributor Guide
------------------

- Issue Tracker: github.com/curveresearch/curvesim/issues
- Source Code: github.com/curveresearch/curvesim

.. toctree::
   :maxdepth: 2

   contributing


Support
-------

If you are having issues, please let us know.  You can reach us via the following

Discord: `Curve #advanced-maths <https://discord.com/channels/729808684359876718/808095641351749722>`_
GitHub: `Curvesim issues <https://github.com/curveresearch/curvesim/issues>`_


License
-------

Portions of the codebase are authorized derivatives of code owned by Curve.fi (Swiss Stake GmbH).  These are the vyper snippets used for testing (`test/fixtures/curve`) and the python code derived from them (`curvesim/pool/stableswap`); there are copyright notices placed appropriately.  The rest of the codebase has an MIT license.
