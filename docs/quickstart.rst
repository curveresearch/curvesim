.. _quickstart:

Quickstart
==========

.. module:: curvesim

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

    >>> pool = curvesim.pool.get("", chain="mainnet")

Now, we have a :class:`Pool <curvesim.pool.Pool>` object called ``pool``.  From
this object we can retrieve state information and see the result of pool operations
such as swaps (exchanges) or adding liquidity.

The pool interface adheres closely to the live smart contract's, so if you are familiar
with the vyper contract, you should feel at home.

For example, to check various state data:
    >>> pool.D()
    >>> pool.A
    >>> pool.rates
    >>> pool.balances

Note already this is already more convenient than how you would need to query the state on
the actual smart contract.

    >>> pool.exchange
    >>> pool.add_liquidity
    >>> pool.remove_liquidity_one_coin()

Let's try doing something a little more interesting... pull a metapool.

    >>> pool = curvesim.pool.get("", chain="mainnet")
    >>> basepool = pool.basepool



Run an arbitrage simulation for a proposed A param
------------------------------------------------------

For a new pool parameter, such as the amplification coefficient ``A``, you would want
to understand the risk-reward profile.  What is the likely fee revenue?  How likely
is the pool to be imbalanced and how deeply?  The ``A`` parameter changes the curvature
of the bonding curve and thus greatly impacts these and other factors.


    >>> payload = {'key1': 'value1', 'key2': 'value2'}
    >>> r = requests.get('https://httpbin.org/get', params=payload)

You can see that the URL has been correctly encoded by printing the URL::

    >>> print(r.url)
    https://httpbin.org/get?key2=value2&key1=value1

Note that any dictionary key whose value is ``None`` will not be added to the
URL's query string.

You can also pass a list of items as a value::

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

