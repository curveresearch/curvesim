.. _install:

Installation
============

Installing Curvesim should be straightforward for most use-cases.  We recommend using the `pip install`
option, but those looking to contribute or use bleeding-edge features may want to use the source
code option.


Python version
---------------
Only versions 3.8 to 3.11 are officially supported.  For users with high performance requirements, we recommend 3.11.


Virtual environments
--------------------
It is highly recommended to use a virtual environment to do an install.  Using a virtual env
ensures that changes in your other packages installed for other projects do not conflict with
Curvesim or its dependencies.  In general, it is considered best practice to separate project
dependencies with virtual envs.

- `Why use virtual envs <https://realpython.com/python-virtual-environments-a-primer/#why-do-you-need-virtual-environments>`_
- `Instructions <https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/#creating-a-virtual-environment>`_ for installing and using a virtual env


$ python3 -m pip install curvesim
---------------------------------

To install Curvesim, simply run this simple command in your terminal of choice::

    $ python3 -m pip install curvesim


Now that you've installed Curvesim, we recommend you check out the :doc:`quickstart`.



Get the source code (developers and advanced users)
----------------------------------------------------

Curvesim is actively developed on GitHub, where the code is
`always available <https://github.com/curveresearch/curvesim>`_.

You can either clone the public repository::

    $ git clone git://github.com/curveresearch/curvesim.git

Or, download the `tarball <https://github.com/curveresearch/curvesim/tarball/main>`_::

    $ curl -OL https://github.com/curveresearch/curvesim/tarball/main
    # optionally, zipball is also available (for Windows users).

Once you have a copy of the source::

    $ cd curvesim

You can make changes and run its modules and scripts like you would in your own project::

    $ python3 -m test.simple_ci

Or you can install it into your site-packages easily::

    $ python3 -m pip install .
