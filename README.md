[![image](https://img.shields.io/pypi/v/curvesim.svg)](https://pypi.org/project/curvesim/)
[![image](https://img.shields.io/pypi/l/curvesim.svg)](https://pypi.org/project/curvesim/)
[![image](https://img.shields.io/pypi/pyversions/curvesim.svg)](https://pypi.org/project/curvesim/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![CI](https://github.com/curveresearch/curvesim/actions/workflows/CI.yml/badge.svg)](https://github.com/curveresearch/curvesim/actions/workflows/CI.yml)
[![Docs](https://readthedocs.org/projects/curvesim/badge/?version=latest)](https://curvesim.readthedocs.io/en/latest)


# CurveSim
CurveSim simulates Curve finance pools with optimal arbitrageurs trading against them. It's primary use is to determine optimal amplitude (A) and fee parameters given historical price and volume feeds.

#### Dependencies:
The maintainers use Python 3.8 or above.  Likely the code should be fine for Python versions from 3.6 onward.

Primary package dependencies: scipy, numpy, pandas, Web3, matplotlib, requests, gmpy2

To avoid dependency issues, it is recommended to use the included `requirements.txt` file in a Python virtual environment (`venv`).



## Documentation

Check out the full documentation at https://curvesim.readthedocs.io/


## Basic Use: Autosim
The autosim() function simulates existing Curve pools with a range of A and/or fee parameters. The function fetches pool properties (e.g., current pool size) and 2 months of price/volume data, runs multiple simulations in parallel, and saves results plots to the "results" directory. 

Curve pools from any chain supported by the [Convex Community Subgraphs](https://thegraph.com/hosted-service/subgraph/convex-community/volume-mainnet) can be simulated directly by inputting the pool's address or symbol. For factory pools, the pool and LP token use the same symbol. For earlier pools, we use the LP token symbol.

### Example:
For example, to simulate 3pool with the default configuration, you could use either its address or the '3crv' LP token symbol (both are case-insensitive):

```python
import curvesim
res = curvesim.autosim("0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7")
res = curvesim.autosim("3crv")
```

To simulate pools on chains other than Ethereum, use the "chain" argument:
```python
import curvesim
res = curvesim.autosim("2crv", chain="arbitrum")
```


### Results:
Plots of the results will be saved to the "results/poolname" (e.g., pools/3crv) directory. The output dictionary, "res", contains pandas dataframes for all of the data plotted in the figures:

* **ar**: annualized returns
* **bal**: balance parameter over time, bal=1 when in perfect balance, and bal=0 when all holdings are in 1 coin
* **pool_value**: time series of pool's value (based on virtual price)
* **depth**: time series of price depth, averaged across pool's coins
* **volume**: time series of pool volume
* **log_returns**: log returns over time
* **err**: time series of absolute price errors, (dy-fee)/dx - p, summed accros coin pairs
* **x**: time series of pool holdings
* **p**: time series of pool precisions (incl. basepool virtual price and/or RAI redemption price)

## Customizing Simulation Parameters
By default, pools are simulated using:
* on-chain or Curve Subgraph data about the pool
* a broad range of A (16 values, 64 to 11,585) and fee (5 values, 0.02 to 0.06%) values
* CoinGecko price/volume data
* 4 parallel threads

However, all of these can be altered using optional keyword arguments.

### Custom A and/or Fee Ranges
Custom A and fee ranges can be specified using the "A" and "fee" arguments. Inputs must be lists or numpy arrays containing lists:

```python
import curvesim
import numpy as np

#Specify A values:
res = curvesim.autosim('3crv', A=np.linspace(1000,20000,20))

#Specify fees (0.04% and 0.05%):
res = curvesim.autosim('3crv', fee=[.0003, .0004])

#Specify custom A range and 0.03% fee
#Note that single fee must still be a list
res = curvesim.autosim('3crv', A=np.linspace(1000,20000,20), fee=[.0003])
```
Additionally, a small number of A/fee values (2 each) can be set for testing purposes: 
```python
res = curvesim.autosim('3crv', test=True)
```


### Overriding Simulation Parameters
The following parameters are automatically specified by autosim(), but can be overridden with keyword arguments:
* **D**: total deposit size; default: fetched from on-chain data
* **vol_mult**: multiplied by market volume to produce trade size limits; default: computed from Curve Subraph data (see Volume Limits for details)
* **feemul**: fee multiplier used in dynamic fee pools; default: specified in poolDF_\*.csv

```python
import curvesim

#Simulate 3pool assuming total deposit of $10B, fee = 0.03%
res = curvesim.autosim('3crv', D=10000000000, fee=[.0003])

#For metapools, specifying D effects the deposit in the metapool, but not the basepool
#Simulate USDN metapool assuming total deposit of $1B, fee = 0.03%
res = curvesim.autosim('usdn3crv', D=1000000000, fee=[.0003])

#Simulate 3pool, limiting volume to 75% of market volume, fee = 0.03% 
#Note: it is not reccomended to adjust this parameter, try vol_mode instead (see below)
res = curvesim.autosim('3crv', vol_mult=.75, fee=[.0003])

#Simulate hypothetical 3pool with dynamic fee like AAVE pool, fee = 0.03% 
res = curvesim.autosim('3crv', feemul=2*10**10, fee=[.0003])
```

### Volume Limits
To approximate realistic market conditions, the "vol_mult" argument is used to limit trade volume at each timepoint in the simulation. By default (vol_mode=1), vol_mult is simply the expected proportion of market volume that goes through the Curve pool (e.g., monthly pool volume / monthly price feed volume). At each timepoint, vol_mult is multiplied by the each coin-pair's market volume to produce a volume limit for each pair, thereby appropriately scaling trade volume while retaining natural volume dynamics. For metapools, vol_mult is computed seperately for the base pool and meta-pool.

In some cases, it may be helpful to limit trade volume differently. In particular, for new coins with little volume for some (but not all) pairs included in the pool, more robust simulations can be achieved by assuming equal volumes across trading pairs. We therefore provide three volume-limiting modes (vol_mode):

* **vol_mode = 1**: limits trade volumes proportionally to market volume for each pair (default)
* **vol_mode = 2**: limits trade volumes equally across pairs
* **vol_mode = 3**: mode 2 for trades with meta-pool asset, mode 1 for basepool-only trades

We reccomend using the default vol_mode 1 in most cases. However, if that returns noisy/uninterpretable results, it may be worth trying mode 2 (for normal pools) or mode 3 (for meta-pools).

### Data Sources
The "src" argument can be used to choose between 3 different data sources:
* **src = "cg"**: CoinGecko API (free); default
* **src = "nomics"**: Nomics API (paid); set `NOMICS_API_KEY` as env variable or in `.env` file.
* **src = "local"**: local data stored in the "data" folder

#### Note on CoinGecko vs. Nomics Data
While Nomics provides 30-minute-interval data for each specific coin-pair, CoinGecko provides prices *per coin* in 1-hour intervals. Each coin's price is computed relative to all its trading pairs and converted to a quote currency (e.g., USD), with volume summed across all trading pairs. Therefore, market volume taken from CoinGecko is often much higher than one can expect for a specific coin-pair. This issue is largely ameloriated by our volume limiting approach, with CoinGecko results typically mirroring Nomics results qualitatively, but it should be noted that CoinGecko data may be less reliable than Nomics data for certain simulations.

For comparison, compare 3pool_cg and 3pool_nomics results in the pools/demo direectory.

### Technical Parameters
Additionally, one can specify:
* **ncpu**: number of CPUs to use for parallel processing (default: 4); for use with profilers, e.g. `cProfile`, use `ncpu=1`.
* **trunc**: a pair of indicies to truncate price/volume data to [trunc[0]:trunc[1]]

## Simulating Hypothetical Pools
If a pool does not already exist, you can directly input the relevant pool values into the psim() function.

