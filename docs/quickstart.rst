.. _quickstart:

Quickstart
==========

This guide will help you get up-and-running with Curvesim.

First, make sure that:

* Curvesim is :ref:`installed <install>`
* Curvesim is :ref:`up-to-date <updates>`


Hello world
------------

Before digging into more interesting examples, let's check the installed package can
run without issues.  In the console, run::

    $ python3 -m curvesim.hello_world


Fetch a pool from a chain
-------------------------

If you know the address of the pool for the chain you want, you can easily start
interacting with it. Curvesim allows you to introspect on the pool's state and use its
functions without submitting actual transactions on chain.

Begin by importing the Curvesim module::

    >>> import curvesim

Let's retrieve the famous 3Pool from Ethereum Mainnet::

    >>> pool = curvesim.pool.get("0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7", "mainnet")

Now, we have a :class:`Pool <curvesim.pool.Pool>` object called ``pool``. Its state is
pulled from daily snapshots of the `Curve volume subgraph <https://github.com/curvefi/volume-subgraphs>`_.
From this object we can retrieve state information and see the result of pool 
operations such as swaps or adding liquidity.

The pool interface adheres closely to the live smart contract's, so if you are familiar
with the vyper contract, you should feel at home.

For example, to check various data about the pool::

    >>> pool.A
    2000

    >>> pool.D()
    792229855185904089753030799

    >>> pool.balances
    [221310603060971366741693471,
     209546983349734000000000000,
     361385319858769000000000000]

Notice this is already more convenient than how you would need to query the state on
the actual smart contract.

You can also easily check the impact of trades or how many LP tokens you receive from
depositing::

    # check out-token amount and fees paid
    >>> dx = 12345 * 10**6
    >>> pool.exchange(2, 1, dx)
    (12340177006, 1234141)

    # check amount of LP tokens received
    >>> amounts = [100 * 10**18, 50 * 10**6, 25 * 10**6]
    >>> pool.add_liquidity(amounts)
    97835056610971313989

You can change pool parameters and see the impact of trades::

    >>> pool.A = 3000
    >>> pool.exchange(2, 1, dx)
    (12341372567, 1234260)


Let's try doing something a little more interesting... pull a metapool::

    # fetch metapool, MIM-3CRV, off Mainnet
    >>> pool = curvesim.pool.get("0x5a6A4D54456819380173272A5E8E9B9904BdF41B", chain="mainnet")
    >>> pool.basepool
    <curvesim.pool.stableswap.pool.Pool at 0x7fa8e1b9f6d0>

    # trade between primary stablecoin of the metapool versus a basepool underlyer
    >>> pool.exchange_underlying(3, 0, dx)
    (12373797212, 4951499)


If you want to dig into the pulled data that was used to construct the pool::

    >>> pool.metadata
    {'name': 'Curve.fi Factory USD Metapool: Magic Internet Money 3Pool',
     'address': '0x5a6A4D54456819380173272A5E8E9B9904BdF41B',
     'chain': 'mainnet',
     'symbol': 'MIM-3LP3CRV-f',
     'version': 1,
     'pool_type': 'METAPOOL_FACTORY',
     'params': {'A': 2000, 'fee': 4000000, 'fee_mul': None},
     'coins': {'names': ['MIM', '3Crv'],
      'addresses': ['0x99D8a9C45b2ecA8864373A26D1459e3Dff1e17F3',
       '0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490']},
     'reserves': {'D': 145335238128075486893034024,
      'by_coin': [124846609724462731254676673, 20488636137518846234875982],
      'virtual_price': 1008020913339661772,
      'tokens': 144178792527792985122545269},
     'basepool': {'name': 'Curve.fi DAI/USDC/USDT',
      'address': '0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7',
      'chain': 'mainnet',
      'symbol': '3Crv',
      'version': 1,
      'pool_type': 'REGISTRY_V1',
      'params': {'A': 2000, 'fee': 1000000, 'fee_mul': None},
      'coins': {'names': ['DAI', 'USDC', 'USDT'],
       'addresses': ['0x6B175474E89094C44Da98b954EedeAC495271d0F',
        '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
        '0xdAC17F958D2ee523a2206206994597C13D831ec7']},
      'reserves': {'D': 792242906269082651836451728,
       'by_coin': [221310603060971366741693471,
        209546983349734012345000000,
        361385319858768987652644961],
       'virtual_price': 1022181723917474348,
       'tokens': 775050940289599852028917731},
      'basepool': None,
      'timestamp': 1667347200,
      'init_kwargs': {'A': 2000,
       'D': 792242906269082651836451728,
       'reserves': [221310603060971366741693471,
        209546983349734012345000000,
        361385319858768987652644961],
       'n': 3,
       'fee': 1000000,
       'fee_mul': None,
       'tokens': 775050940289599852028917731}},
     'timestamp': 1667347200,
     'init_kwargs': {'A': 2000,
      'D': 145335238128075486893034024,
      'reserves': [124846609724462731254676673, 20488636137518846234875982],
      'n': 2,
      'fee': 4000000,
      'fee_mul': None,
      'tokens': 144178792527792985122545269}}




Run an arbitrage simulation for a proposed A parameter
------------------------------------------------------

Tuning a pool parameter, such as the amplification coefficient ``A``, can greatly affect the
risk-reward profile.  The ``A`` parameter alters the curvature of the bonding curve, directly
impacting the pool's ability to handle large trades while holding imbalanced reserves.::

    >>> import curvesim
    >>> mim = "0x5a6A4D54456819380173272A5E8E9B9904BdF41B"
    >>> res = curvesim.autosim(mim, chain="mainnet", A=875)
    Fetching CoinGecko price data...
    Fetching historical volume...
    Volume Multipliers:
    [9.59195904e-07 9.59195904e-07 9.59195904e-07 2.36911915e-05
     2.36911915e-05 2.36911915e-05]
    [MIM-3LP3CRV-f] Simulating with {'A': 875, 'fee': 1000000}
    [MIM-3LP3CRV-f] Simulating with {'A': 875, 'fee': 2000000}
    [MIM-3LP3CRV-f] Simulating with {'A': 875, 'fee': 3000000}
    [MIM-3LP3CRV-f] Simulating with {'A': 875, 'fee': 4000000}

The ``res`` dictionary holds different time series showing different aspects of risk and reward, such as annualized returns, pool total value, imbalance factor, and volume.

Charts are saved in the ``results`` folder.

Likely you will want to see the impact over a range of ``A`` values.  The ``A`` and ``fee`` parameters will accept either a integer or iterables of integers; note ``fee`` values are in units of basis points multiplied by 10**6.::
    
    >>> res = curvesim.autosim(mim, chain="mainnet", A=range(500, 1500, 250), fee=4000000)
    Fetching CoinGecko price data...
    Fetching historical volume...
    Volume Multipliers:
    [9.59195904e-07 9.59195904e-07 9.59195904e-07 2.37521074e-05
     2.37521074e-05 2.37521074e-05]
    [MIM-3LP3CRV-f] Simulating with {'A': 750, 'fee': 4000000}
    [MIM-3LP3CRV-f] Simulating with {'A': 1000, 'fee': 4000000}
    [MIM-3LP3CRV-f] Simulating with {'A': 1250, 'fee': 4000000}
    [MIM-3LP3CRV-f] Simulating with {'A': 500, 'fee': 4000000}

Run an arbitrage simulation varying multiple parameters
--------------------------------------------------------

You may also want to see how different ``A`` and ``fee`` parameters perform in conjuction.
If you input multiple iterables for parameters, each possible combination of parameters is simulated::

    >>> res = curvesim.autosim(mim, chain="mainnet", A=[100, 1000], fee=[3000000, 4000000])
    Fetching CoinGecko price data...
    Fetching historical volume...
    Volume Multipliers:
    [9.59195904e-07 9.59195904e-07 9.59195904e-07 2.37521074e-05
     2.37521074e-05 2.37521074e-05]
    [MIM-3LP3CRV-f] Simulating with {'A': 100, 'fee': 3000000}
    [MIM-3LP3CRV-f] Simulating with {'A': 100, 'fee': 4000000}
    [MIM-3LP3CRV-f] Simulating with {'A': 1000, 'fee': 3000000}
    [MIM-3LP3CRV-f] Simulating with {'A': 1000, 'fee': 4000000}


Fine-tuning the simulator
-------------------------
Other helpful parameters for :func:`.autosim` are:

    - ``src``: data source for prices and volumes.  Allowed values are 'coingecko', 'nomics', or 'local'
    - ``ncpu``: Number of cores to use.
    - ``days``: Number of days to fetch data for.
    - ``vol_mode``: Modes for limiting trade volume

      - 1: limits trade volumes proportionally to market volume for each pair
      - 2: limits trade volumes equally across pairs
      - 3: mode 2 for trades with meta-pool asset, mode 1 for basepool-only trades

    - ``test``: Sets ``A`` and ``fee`` params to a small set of values for testing purposes.


Tips
----

Price data source
^^^^^^^^^^^^^^^^^

By default, Curvesim uses Coingecko pricing and volume data.  You can specify 
Nomics as the data provider, by using ``src='nomics'`` in simulations

In order to use this feature you will need to have the ``NOMICS_API_KEY``
environment variable set. You can manually set one this running the python
process, although for your convenience, Curvesim will automatically load any
env variables it finds in a local ``.env`` file.

Parallel processing
^^^^^^^^^^^^^^^^^^^
By default, Curvesim will use the maximum number of cores available to run
simulations.  You can specify the exact number through the `ncpu` option.

For profiling the code, it is recommended to use ``ncpu=1``, as common
profilers (such as ``cProfile``) will not produce accurate results otherwise.

Note: Using the Nomics data source requires setting the NOMICS_API_KEY OS environment
variable with a paid nomics API key


Errors and Exceptions
---------------------

All exceptions that Curvesim explicitly raises inherit from
:exc:`curvesim.exceptions.CurvesimException`.

Here are some common error types that may be useful to know about.

-----------------------

Ready for more? Check out the :ref:`advanced <advanced>` section.

