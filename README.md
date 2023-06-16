# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/curveresearch/curvesim/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                 |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|----------------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| curvesim/\_\_init\_\_.py                             |        5 |        0 |        0 |        0 |    100% |           |
| curvesim/\_bonding\_curve/\_\_init\_\_.py            |       40 |       35 |       20 |        0 |      8% |     41-90 |
| curvesim/\_order\_book/\_\_init\_\_.py               |       53 |       48 |       12 |        0 |      8% |52-100, 104-130 |
| curvesim/exceptions/\_\_init\_\_.py                  |       19 |        0 |        0 |        0 |    100% |           |
| curvesim/iterators/\_\_init\_\_.py                   |        0 |        0 |        0 |        0 |    100% |           |
| curvesim/iterators/param\_samplers/\_\_init\_\_.py   |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/iterators/param\_samplers/grid.py           |       54 |       24 |       26 |        4 |     50% |68-77, 84, 88-98, 102-106 |
| curvesim/iterators/price\_samplers/\_\_init\_\_.py   |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/iterators/price\_samplers/price\_volume.py  |       22 |        1 |        4 |        0 |     96% |        74 |
| curvesim/logging.py                                  |       45 |        0 |        6 |        1 |     98% |    94->96 |
| curvesim/metrics/\_\_init\_\_.py                     |        6 |        0 |        2 |        0 |    100% |           |
| curvesim/metrics/base.py                             |      123 |       11 |       31 |        4 |     90% |146-148, 221, 291-294, 342-343, 368->exit, 369, 371->376 |
| curvesim/metrics/metrics.py                          |      179 |       23 |       16 |        0 |     84% |133-163, 170-173, 181-190, 193-197 |
| curvesim/metrics/results/\_\_init\_\_.py             |        3 |        0 |        0 |        0 |    100% |           |
| curvesim/metrics/results/make\_results.py            |       28 |        0 |       10 |        0 |    100% |           |
| curvesim/metrics/results/sim\_results.py             |       35 |       12 |       12 |        3 |     55% |62-65, 91-93, 120, 128-131 |
| curvesim/metrics/state\_log/\_\_init\_\_.py          |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/metrics/state\_log/log.py                   |       28 |        0 |       10 |        0 |    100% |           |
| curvesim/metrics/state\_log/pool\_parameters.py      |       17 |        0 |        6 |        0 |    100% |           |
| curvesim/metrics/state\_log/pool\_state.py           |       12 |        0 |        2 |        0 |    100% |           |
| curvesim/network/\_\_init\_\_.py                     |        0 |        0 |        0 |        0 |    100% |           |
| curvesim/network/coingecko.py                        |      113 |       37 |       22 |        2 |     64% |62-66, 148, 161-169, 173-184, 188-200, 204-214 |
| curvesim/network/http.py                             |       39 |        5 |        8 |        1 |     87% |42->45, 49-54 |
| curvesim/network/subgraph.py                         |      135 |       55 |       48 |        3 |     55% |78, 112-143, 148, 211-227, 231->235, 438-464, 497-521 |
| curvesim/network/utils.py                            |       38 |        6 |        8 |        1 |     80% |41-42, 68-71 |
| curvesim/network/web3.py                             |       70 |        5 |       16 |        5 |     86% |62-63, 139->147, 143-144, 147->152, 176 |
| curvesim/overrides/\_\_init\_\_.py                   |        9 |        3 |        4 |        1 |     54% |     40-42 |
| curvesim/pipelines/\_\_init\_\_.py                   |       21 |        5 |       12 |        1 |     76% |     75-79 |
| curvesim/pipelines/simple/\_\_init\_\_.py            |       29 |        0 |        4 |        1 |     97% |  113->117 |
| curvesim/pipelines/simple/strategy.py                |       10 |        0 |        0 |        0 |    100% |           |
| curvesim/pipelines/simple/trader.py                  |       56 |        4 |       18 |        0 |     95% |   138-144 |
| curvesim/pipelines/templates/\_\_init\_\_.py         |        5 |        0 |        0 |        0 |    100% |           |
| curvesim/pipelines/templates/sim\_assets.py          |        8 |        0 |        0 |        0 |    100% |           |
| curvesim/pipelines/templates/sim\_pool.py            |        7 |        0 |        0 |        0 |    100% |           |
| curvesim/pipelines/templates/strategy.py             |       19 |        0 |        2 |        0 |    100% |           |
| curvesim/pipelines/templates/trader.py               |       40 |        4 |       12 |        0 |     81% |18, 31, 35-36 |
| curvesim/pipelines/utils.py                          |       35 |       27 |       16 |        0 |     16% |40-50, 54-64, 68-93 |
| curvesim/pipelines/vol\_limited\_arb/\_\_init\_\_.py |       37 |       21 |       10 |        0 |     38% |   106-143 |
| curvesim/pipelines/vol\_limited\_arb/strategy.py     |       14 |        4 |        0 |        0 |     71% |28-29, 32-33 |
| curvesim/pipelines/vol\_limited\_arb/trader.py       |       80 |       71 |       30 |        0 |      8% |37-40, 71-140, 168-213 |
| curvesim/plot/\_\_init\_\_.py                        |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/plot/altair/\_\_init\_\_.py                 |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/plot/altair/chart\_properties.py            |       36 |       26 |       14 |        0 |     20% |8-15, 19-24, 28-33, 37, 41-53 |
| curvesim/plot/altair/make\_chart.py                  |       30 |       23 |       10 |        0 |     18% |12-26, 30-53 |
| curvesim/plot/altair/results/\_\_init\_\_.py         |        0 |        0 |        0 |        0 |    100% |           |
| curvesim/plot/altair/results/make\_page.py           |       59 |       45 |       16 |        0 |     19% |13-19, 23-25, 29-38, 42-56, 60-65, 69-72, 76-88 |
| curvesim/plot/altair/results/preprocessing.py        |       35 |       28 |       10 |        0 |     16% |7-10, 14-33, 37-39, 43, 47-54 |
| curvesim/plot/altair/results/result\_plotter.py      |       25 |       14 |        0 |        0 |     44% |15-17, 25-30, 38-43, 53 |
| curvesim/plot/altair/results/result\_selectors.py    |       40 |       32 |        6 |        0 |     17% |14-26, 33-43, 47-58, 62-72, 76-86, 90-92 |
| curvesim/plot/altair/results/tooltip.py              |       10 |        8 |        4 |        0 |     14% |      5-15 |
| curvesim/plot/altair/selectors.py                    |       32 |       24 |       10 |        0 |     19% |18-28, 32-44, 48-68, 72 |
| curvesim/plot/altair/styles.py                       |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/plot/result\_plotter.py                     |       16 |        9 |        8 |        0 |     29% |     53-63 |
| curvesim/pool/\_\_init\_\_.py                        |       50 |       25 |       18 |        4 |     43% |106-134, 177-195, 217, 219, 223, 233-236 |
| curvesim/pool/base.py                                |       50 |       21 |       18 |        4 |     49% |29-31, 36-38, 45, 52, 57-59, 66, 71-73, 80, 85-89 |
| curvesim/pool/cryptoswap/\_\_init\_\_.py             |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/pool/cryptoswap/pool.py                     |      538 |       69 |      156 |       36 |     83% |153, 158, 161, 163->166, 169-176, 182, 228, 230, 260, 285, 299, 302, 316, 318, 320, 347, 360-361, 374, 388, 396, 469->478, 474, 516->526, 531-532, 536-559, 684->692, 744, 794->793, 804, 818->842, 820-840, 845-848, 1128, 1141, 1163, 1167, 1187 |
| curvesim/pool/sim\_interface/\_\_init\_\_.py         |        4 |        0 |        0 |        0 |    100% |           |
| curvesim/pool/sim\_interface/metapool.py             |       81 |        3 |       26 |        3 |     94% |37, 64, 75 |
| curvesim/pool/sim\_interface/pool.py                 |       36 |        0 |        4 |        0 |    100% |           |
| curvesim/pool/sim\_interface/raipool.py              |       10 |        5 |        0 |        0 |     50% |19-21, 33-34 |
| curvesim/pool/sim\_interface/simpool.py              |       32 |        3 |       14 |        3 |     87% |32, 36, 61 |
| curvesim/pool/snapshot.py                            |       55 |        0 |        2 |        0 |    100% |           |
| curvesim/pool/stableswap/\_\_init\_\_.py             |        4 |        0 |        0 |        0 |    100% |           |
| curvesim/pool/stableswap/metapool.py                 |      278 |       10 |       82 |        7 |     95% |84, 349, 483->495, 502, 636-638, 670, 755, 776, 833 |
| curvesim/pool/stableswap/pool.py                     |      198 |        2 |       52 |        2 |     98% |388->400, 407, 567 |
| curvesim/pool/stableswap/raipool.py                  |       14 |        9 |        2 |        0 |     31% |32, 35-41, 44-46 |
| curvesim/pool\_data/\_\_init\_\_.py                  |       12 |        3 |        0 |        0 |     75% |     41-44 |
| curvesim/pool\_data/cache.py                         |       61 |       42 |       14 |        0 |     25% |36-52, 63-64, 70-71, 95-99, 102-118, 144-148, 151-159 |
| curvesim/pool\_data/metadata/\_\_init\_\_.py         |       35 |        5 |        6 |        1 |     85% |50, 61-62, 67-68 |
| curvesim/pool\_data/metadata/base.py                 |       33 |        0 |        0 |        0 |    100% |           |
| curvesim/pool\_data/metadata/cryptoswap.py           |       25 |        0 |        8 |        0 |    100% |           |
| curvesim/pool\_data/metadata/stableswap.py           |       45 |        0 |       18 |        0 |    100% |           |
| curvesim/pool\_data/queries.py                       |       16 |        3 |        4 |        0 |     85% |     46-50 |
| curvesim/price\_data/\_\_init\_\_.py                 |       10 |        4 |        6 |        1 |     44% |     51-55 |
| curvesim/price\_data/sources.py                      |       31 |       19 |        4 |        0 |     34% |11-29, 41-52 |
| curvesim/sim/\_\_init\_\_.py                         |       38 |       31 |       20 |        0 |     12% |138-151, 155-193 |
| curvesim/utils.py                                    |       41 |       10 |       19 |        6 |     70% |45, 48, 84, 96-105, 107->exit, 108 |
| curvesim/version.py                                  |        7 |        0 |        0 |        0 |    100% |           |
|                                            **TOTAL** | **3435** |  **874** |  **918** |   **94** | **71%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/curveresearch/curvesim/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/curveresearch/curvesim/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/curveresearch/curvesim/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/curveresearch/curvesim/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fcurveresearch%2Fcurvesim%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/curveresearch/curvesim/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.