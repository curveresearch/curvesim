[![image](https://img.shields.io/pypi/v/curvesim.svg)](https://pypi.org/project/curvesim/)
[![image](https://img.shields.io/pypi/l/curvesim.svg)](https://pypi.org/project/curvesim/)
[![image](https://img.shields.io/pypi/pyversions/curvesim.svg)](https://pypi.org/project/curvesim/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![CI](https://github.com/curveresearch/curvesim/actions/workflows/CI.yml/badge.svg)](https://github.com/curveresearch/curvesim/actions/workflows/CI.yml)
[![Docs](https://readthedocs.org/projects/curvesim/badge/?version=latest)](https://curvesim.readthedocs.io/en/latest)
![badge](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/chanhosuh/3da3c072e081f4509ebdd09c63e6ede5/raw/curvesim_coverage_badge.json)


# Curvesim
Curvesim simulates Curve pools with optimal arbitrageurs trading against them to determine reasonable risk and reward parameters, such as amplitude (A) and fee, given historical price and volume feeds.

Users can re-use simulation components to simulate custom strategies and generate custom metrics.  Pool objects enable simpler integration with Curve pools for both manual and automated analytics usage.


#### Dependencies:
Python versions 3.8 - 3.11 are supported.

Primary package dependencies: scipy, numpy, pandas, altair, matplotlib, requests, web3, gmpy2

When working on the codebase, to avoid dependency issues it is recommended to use the included `requirements.txt` file in a Python virtual environment (`venv`).  Python 3.10 is required for this.


## Documentation
Check out the full documentation at https://curvesim.readthedocs.io/.  We recommend starting with the "Quickstart" guide.

## Licensing
Portions of the codebase are authorized derivatives of code owned by Curve.fi (Swiss Stake GmbH).  These are the vyper snippets used for testing (`test/fixtures/curve`) and the python code derived from them (`curvesim/pool/stableswap` and `curvesim/pool/cryptoswap`); there are copyright notices placed appropriately.  The rest of the codebase has an MIT license.

## Basic Use: Autosim
The autosim() function simulates existing Curve pools with a range of A and/or fee parameters. The function fetches pool properties (e.g., current pool size) and 2 months of price/volume data, runs multiple simulations in parallel, and returns a results object that can be introspected or generate charts.

Curve pools from any chain supported by the [Convex Community Subgraphs](https://thegraph.com/hosted-service/subgraph/convex-community/volume-mainnet) can be simulated directly by inputting the pool's address.

### Example:
To simulate 3pool with the default configuration:

```python
import curvesim
res = curvesim.autosim("0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7")
```

To simulate pools on chains other than Ethereum, use the "chain" argument:

```python
import curvesim
# run sim on Arbitrum 2Crv
res = curvesim.autosim("0x7f90122BF0700F9E7e1F688fe926940E8839F353", chain="arbitrum")
```


## Simulation Results
The simulation returns a SimResults object that can plot simulation metrics or return them as DataFrames.

### Plotting results:
```python
#Plot results using Altair
res.plot() 

#Save plot results as results.html
res.plot(save_as="results.html")

```

### Example output:
![Alt text](/docs/images/plot_summary_screenshot.png?raw=true "Summary statistics")

![Alt text](/docs/images/plot_timeseries_screenshot.png?raw=true "Timeseries data")



### Summary statistics:
```python
>>> res.summary()
metric pool_value_virtual         pool_value  ...   pool_volume price_error
stat   annualized_returns annualized_returns  ...           sum      median
0                0.003580           0.005156  ...  2.286297e+09    0.000669
1                0.006158           0.007741  ...  1.966299e+09    0.000600
2                0.007760           0.009348  ...  1.652965e+09    0.000775
3                0.008611           0.010200  ...  1.377299e+09    0.000956
4                0.003760           0.005439  ...  2.400174e+09    0.000777
..                    ...                ...  ...           ...         ...
59               0.009523           0.012018  ...  1.521524e+09    0.001155
60               0.003742           0.006247  ...  2.388746e+09    0.001063
61               0.006533           0.009082  ...  2.084530e+09    0.000915
62               0.008344           0.010894  ...  1.775963e+09    0.000974
63               0.009402           0.011974  ...  1.502494e+09    0.001133
```

### Timeseries data:
```python
>>> res.data()
       run                 timestamp  ...      pool_volume  price_error
0        0 2023-03-21 23:30:00+00:00  ...  15206414.533633     0.005310
1        0 2023-03-22 00:30:00+00:00  ...    7278720.40969     0.002029
2        0 2023-03-22 01:30:00+00:00  ...   6125207.553072     0.000100
3        0 2023-03-22 02:30:00+00:00  ...    7066251.03295     0.000100
4        0 2023-03-22 03:30:00+00:00  ...   3512782.000945     0.000299
...    ...                       ...  ...              ...          ...
93755   63 2023-05-21 19:30:00+00:00  ...    879436.331564     0.000893
93756   63 2023-05-21 20:30:00+00:00  ...              0.0     0.001091
93757   63 2023-05-21 21:30:00+00:00  ...    720837.826971     0.000800
93758   63 2023-05-21 22:30:00+00:00  ...    445967.506177     0.001414
93759   63 2023-05-21 23:30:00+00:00  ...    391060.986022     0.000906
```




## Customizing Simulation Parameters
By default, pools are simulated using:
* on-chain or Curve Subgraph data about the pool
* a broad range of A (16 values, 64 to 11,585) and fee (5 values, 0.02 to 0.06%) values
* CoinGecko price/volume data
* all detected CPU cores

However, all of these can be altered using optional keyword arguments.

### Custom A and/or Fee Ranges
Custom A and fee ranges can be specified using the "A" and "fee" arguments. Inputs must be lists or numpy arrays containing lists:

```python
import curvesim
import numpy as np

#Specify A values:
res = curvesim.autosim('0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7', A=range(1000,2001,100))

#Specify fees (0.03% and 0.04% with 10 decimal precision):
res = curvesim.autosim('0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7', fee=[3000000, 4000000])

#Specify custom A range and 0.03% fee
res = curvesim.autosim('0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7', A=range(1000,2001,100), fee=3000000)
```
Additionally, a small number of A/fee values (2 each) can be set for testing purposes: 
```python
res = curvesim.autosim('0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7', test=True)
```


### Overriding Simulation Parameters
The following parameters are automatically specified by autosim(), but can be overridden with keyword arguments:
* **D**: total deposit size; default: fetched from on-chain data
* **vol_mult**: multiplied by market volume to produce trade size limits; default: computed from Curve Subraph data (see Volume Limits for details)
* **feemul**: fee multiplier used in dynamic fee pools

```python
import curvesim

#Simulate 3pool assuming total deposit of $10B, fee = 0.03%
res = curvesim.autosim('0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7', D=10000000000, fee=3000000)

#For metapools, specifying D effects the deposit in the metapool, but not the basepool
#Simulate USDN metapool assuming total deposit of $1B, fee = 0.03%
res = curvesim.autosim('0x0f9cb53Ebe405d49A0bbdBD291A65Ff571bC83e1', D=1000000000, fee=3000000)

#Simulate 3pool, limiting volume to 75% of market volume, fee = 0.03% 
#Note: it is not reccomended to adjust this parameter, try vol_mode instead (see below)
res = curvesim.autosim('0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7', vol_mult=.75, fee=3000000)

#Simulate hypothetical 3pool with dynamic fee like AAVE pool, fee = 0.03% 
res = curvesim.autosim('0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7', feemul=2*10**10, fee=3000000)
```

### Volume Limits
To approximate realistic market conditions, the "vol_mult" argument is used to limit trade volume at each timepoint in the simulation. By default (vol_mode=1), vol_mult is simply the expected proportion of market volume that goes through the Curve pool (e.g., monthly pool volume / monthly price feed volume). At each timepoint, vol_mult is multiplied by the each coin-pair's market volume to produce a volume limit for each pair, thereby appropriately scaling trade volume while retaining natural volume dynamics. For metapools, vol_mult is computed seperately for the base pool and meta-pool.

In some cases, it may be helpful to limit trade volume differently. In particular, for new coins with little volume for some (but not all) pairs included in the pool, more robust simulations can be achieved by assuming equal volumes across trading pairs. We therefore provide three volume-limiting modes (vol_mode):

* **vol_mode = 1**: limits trade volumes proportionally to market volume for each pair (default)
* **vol_mode = 2**: limits trade volumes equally across pairs
* **vol_mode = 3**: mode 2 for trades with meta-pool asset, mode 1 for basepool-only trades

We reccomend using the default vol_mode 1 in most cases. However, if that returns noisy/uninterpretable results, it may be worth trying mode 2 (for normal pools) or mode 3 (for meta-pools).

### Data Sources
The "src" argument can be used to choose between two different data sources:
* **src = "coingecko"**: CoinGecko API (free); default
* **src = "local"**: local data stored in the "data" folder

Note that Nomics data is no longer supported since they went out of service.

#### Note on CoinGecko Data
Coingecko price/volume data is computed using all trading pairs for each coin, with volume summed across all pairs. Therefore, market volume taken from CoinGecko can be much higher than that of any specific trading pair used in a simulation. This issue is largely ameloriated by our volume limiting approach, with CoinGecko results typically mirroring results from pairwise data, but it should be noted that CoinGecko data may be less reliable than more granular data for certain simulations.

### Technical Parameters
Additionally, one can specify:
* **ncpu**: number of CPUs to use for parallel processing (default: all cores); for use with profilers, e.g. `cProfile`, use `ncpu=1`.
* **days**: the number of days worth of data to use in the simulation (default: 60)
