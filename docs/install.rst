.. _install:

Installation of Curvesim
========================

Installing Curvesim should be straightforward for most use-cases.  We recommend using the `pip install`
option, but those looking to contribute or use bleeding-edge features may want to use the source
code option.


$ python3 -m pip install curvesim
--------------------------------

To install Curvesim, simply run this simple command in your terminal of choice::

    $ python3 -m pip install curvesim


Get the Source Code
-------------------

Curvesim is actively developed on GitHub, where the code is
`always available <https://github.com/curveresearch/curvesim>`_.

You can either clone the public repository::

    $ git clone git://github.com/curveresearch/curvesim.git

Or, download the `tarball <https://github.com/curveresearch/curvesim/tarball/main>`_::

    $ curl -OL https://github.com/curveresearch/curvesim/tarball/main
    # optionally, zipball is also available (for Windows users).

Once you have a copy of the source, you can embed it in your own Python
package, or install it into your site-packages easily::

    $ cd curvesim
    $ python3 -m pip install .
