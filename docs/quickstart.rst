.. _quickstart:

Quickstart
==========

This guide will help you get up-and-running with Curvesim.

First, check that:

* Curvesim is :ref:`installed <install>`
* Curvesim is :ref:`up-to-date <updates>`


Let's get started with some simple examples.


Fetch a pool from a chain
-------------------------

If you know the address of the pool for the chain you want, you can easily start
interacting with it (note this is introspecting on the pool state and using its
functions; Curvesim doesn't actually submit transacions, i.e. write data to the
chain and alter the real pool state.)

Begin by importing the Curvesim module::

    >>> import curvesim

Let's retrieve the famous 3Pool from Ethereum Mainnet::

    >>> pool = curvesim.pool.get("0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7", "mainnet")

Now, we have a :class:`Pool <curvesim.pool.Pool>` object called ``pool``.  From
this object we can retrieve state information and see the result of pool operations
such as swaps (exchanges) or adding liquidity.

The pool interface adheres closely to the live smart contract's, so if you are familiar
with the vyper contract, you should feel at home.

For example, to check various data about the pool::

    >>> pool.A
    2000

    >>> pool.D()
    792229855185904089753030799

    >>> pool.x
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




Run an arbitrage simulation for a proposed A param
------------------------------------------------------

For a new pool parameter, such as the amplification coefficient ``A``, you would want
to understand the risk-reward profile.  What is the likely fee revenue?  How likely
is the pool to be imbalanced and how deeply?  The ``A`` parameter changes the curvature
of the bonding curve and thus greatly impacts these and other factors.

    >>> import curvesim
    >>> curvesim.autosim("0x5a6A4D54456819380173272A5E8E9B9904BdF41B", chain="mainnet", A=875)


    >>> payload = {'key1': 'value1', 'key2': ['value2', 'value3']}

    >>> r = requests.get('https://httpbin.org/get', params=payload)
    >>> print(r.url)
    https://httpbin.org/get?key1=value1&key2=value2&key2=value3




Errors and Exceptions
---------------------

In the event of a network problem (e.g. DNS failure, refused connection, etc),
Requests will raise a :exc:`~requests.exceptions.ConnectionError` exception.

:meth:`Response.raise_for_status() <requests.Response.raise_for_status>` will
raise an :exc:`~requests.exceptions.HTTPError` if the HTTP request
returned an unsuccessful status code.

If a request times out, a :exc:`~requests.exceptions.Timeout` exception is
raised.

If a request exceeds the configured number of maximum redirections, a
:exc:`~requests.exceptions.TooManyRedirects` exception is raised.

All exceptions that Requests explicitly raises inherit from
:exc:`requests.exceptions.RequestException`.

-----------------------

Ready for more? Check out the :ref:`advanced <advanced>` section.

