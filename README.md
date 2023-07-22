# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/curveresearch/curvesim/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                                |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|-------------------------------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| curvesim/\_\_init\_\_.py                                            |        5 |        0 |        0 |        0 |    100% |           |
| curvesim/\_bonding\_curve/\_\_init\_\_.py                           |       40 |       35 |       20 |        0 |      8% |     41-90 |
| curvesim/\_order\_book/\_\_init\_\_.py                              |       53 |       48 |       12 |        0 |      8% |52-100, 104-130 |
| curvesim/exceptions/\_\_init\_\_.py                                 |       20 |        0 |        0 |        0 |    100% |           |
| curvesim/iterators/\_\_init\_\_.py                                  |        0 |        0 |        0 |        0 |    100% |           |
| curvesim/iterators/param\_samplers/\_\_init\_\_.py                  |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/iterators/param\_samplers/parameterized\_pool\_iterator.py |       48 |        1 |        8 |        1 |     96% |        33 |
| curvesim/iterators/param\_samplers/pool\_mixins.py                  |       41 |       11 |        8 |        0 |     69% |42, 46, 63-74 |
| curvesim/iterators/price\_samplers/\_\_init\_\_.py                  |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/iterators/price\_samplers/price\_volume.py                 |       24 |        1 |        4 |        0 |     96% |        90 |
| curvesim/logging.py                                                 |       45 |        0 |        6 |        1 |     98% |    94->96 |
| curvesim/metrics/\_\_init\_\_.py                                    |        6 |        0 |        2 |        0 |    100% |           |
| curvesim/metrics/base.py                                            |      123 |       11 |       31 |        4 |     90% |146-148, 221, 291-294, 342-343, 368->exit, 369, 371->376 |
| curvesim/metrics/metrics.py                                         |      171 |        0 |       22 |        0 |    100% |           |
| curvesim/metrics/results/\_\_init\_\_.py                            |        3 |        0 |        0 |        0 |    100% |           |
| curvesim/metrics/results/make\_results.py                           |       28 |        0 |       10 |        0 |    100% |           |
| curvesim/metrics/results/sim\_results.py                            |       35 |       12 |       12 |        3 |     55% |62-65, 91-93, 120, 128-131 |
| curvesim/metrics/state\_log/\_\_init\_\_.py                         |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/metrics/state\_log/log.py                                  |       28 |        0 |       10 |        0 |    100% |           |
| curvesim/metrics/state\_log/pool\_parameters.py                     |       17 |        0 |        6 |        0 |    100% |           |
| curvesim/metrics/state\_log/pool\_state.py                          |       12 |        0 |        2 |        0 |    100% |           |
| curvesim/network/\_\_init\_\_.py                                    |        0 |        0 |        0 |        0 |    100% |           |
| curvesim/network/coingecko.py                                       |       76 |        6 |       12 |        2 |     91% |62-66, 148 |
| curvesim/network/http.py                                            |       39 |        5 |        8 |        1 |     87% |42->45, 49-54 |
| curvesim/network/subgraph.py                                        |      136 |       55 |       48 |        2 |     56% |78, 112-143, 148, 211-227, 439-465, 498-522 |
| curvesim/network/utils.py                                           |       38 |        6 |        8 |        1 |     80% |41-42, 68-71 |
| curvesim/network/web3.py                                            |       70 |        5 |       16 |        5 |     86% |62-63, 139->147, 143-144, 147->152, 176 |
| curvesim/overrides/\_\_init\_\_.py                                  |        9 |        3 |        4 |        1 |     54% |     40-42 |
| curvesim/pipelines/\_\_init\_\_.py                                  |       21 |        5 |       12 |        1 |     76% |     75-79 |
| curvesim/pipelines/simple/\_\_init\_\_.py                           |       28 |        0 |        4 |        1 |     97% |  113->118 |
| curvesim/pipelines/simple/strategy.py                               |       10 |        0 |        0 |        0 |    100% |           |
| curvesim/pipelines/simple/trader.py                                 |       55 |        4 |       18 |        0 |     95% |   127-133 |
| curvesim/pipelines/utils.py                                         |       46 |       36 |       14 |        0 |     17% |40-55, 59-72, 76-104, 108-110 |
| curvesim/pipelines/vol\_limited\_arb/\_\_init\_\_.py                |       37 |       21 |       10 |        0 |     38% |   111-149 |
| curvesim/pipelines/vol\_limited\_arb/strategy.py                    |       18 |        7 |        4 |        0 |     50% |28-29, 32-33, 37-39 |
| curvesim/pipelines/vol\_limited\_arb/trader.py                      |       77 |       68 |       30 |        0 |      8% |37-40, 70-136, 164-207 |
| curvesim/plot/\_\_init\_\_.py                                       |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/plot/altair/\_\_init\_\_.py                                |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/plot/altair/chart\_properties.py                           |       35 |       25 |       14 |        0 |     20% |31-38, 61-66, 83-88, 130-142 |
| curvesim/plot/altair/make\_chart.py                                 |       30 |       23 |       10 |        0 |     18% |45-59, 87-110 |
| curvesim/plot/altair/results/\_\_init\_\_.py                        |        0 |        0 |        0 |        0 |    100% |           |
| curvesim/plot/altair/results/make\_page.py                          |       59 |       45 |       16 |        0 |     19% |40-46, 71-73, 98-107, 126-140, 165-170, 195-198, 223-235 |
| curvesim/plot/altair/results/preprocessing.py                       |       35 |       28 |       10 |        0 |     16% |32-35, 61-80, 101-103, 122, 141-148 |
| curvesim/plot/altair/results/result\_plotter.py                     |       25 |       14 |        0 |        0 |     44% |15-17, 25-30, 38-43, 53 |
| curvesim/plot/altair/results/result\_selectors.py                   |       40 |       32 |        6 |        0 |     17% |31-43, 65-75, 94-105, 127-137, 159-169, 188-190 |
| curvesim/plot/altair/results/tooltip.py                             |       10 |        8 |        4 |        0 |     14% |      6-16 |
| curvesim/plot/altair/selectors.py                                   |       32 |       24 |       10 |        0 |     19% |59-69, 97-109, 134-154, 179 |
| curvesim/plot/altair/styles.py                                      |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/plot/result\_plotter.py                                    |       16 |        9 |        8 |        0 |     29% |     53-63 |
| curvesim/pool/\_\_init\_\_.py                                       |       54 |       31 |       22 |        2 |     33% |106-134, 177-195, 218-231, 241-244 |
| curvesim/pool/base.py                                               |       50 |       21 |       18 |        4 |     49% |29-31, 36-38, 45, 52, 57-59, 66, 71-73, 80, 85-89 |
| curvesim/pool/cryptoswap/\_\_init\_\_.py                            |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/pool/cryptoswap/pool.py                                    |      538 |       69 |      156 |       36 |     83% |153, 158, 161, 163->166, 169-176, 182, 228, 230, 260, 285, 299, 302, 316, 318, 320, 347, 360-361, 374, 388, 396, 469->478, 474, 516->526, 531-532, 536-559, 684->692, 744, 794->793, 804, 818->842, 820-840, 845-848, 1128, 1141, 1163, 1167, 1187 |
| curvesim/pool/sim\_interface/\_\_init\_\_.py                        |        4 |        0 |        0 |        0 |    100% |           |
| curvesim/pool/sim\_interface/asset\_indices.py                      |       22 |        1 |        8 |        1 |     93% |        60 |
| curvesim/pool/sim\_interface/metapool.py                            |       86 |        3 |       24 |        3 |     95% |25, 93, 96 |
| curvesim/pool/sim\_interface/pool.py                                |       42 |        1 |        4 |        1 |     96% |        17 |
| curvesim/pool/sim\_interface/raipool.py                             |       10 |        2 |        0 |        0 |     80% |     33-34 |
| curvesim/pool/snapshot.py                                           |       55 |        0 |        2 |        0 |    100% |           |
| curvesim/pool/stableswap/\_\_init\_\_.py                            |        4 |        0 |        0 |        0 |    100% |           |
| curvesim/pool/stableswap/metapool.py                                |      278 |       10 |       82 |        7 |     95% |84, 349, 483->495, 502, 636-638, 670, 755, 776, 833 |
| curvesim/pool/stableswap/pool.py                                    |      198 |        2 |       52 |        2 |     98% |388->400, 407, 567 |
| curvesim/pool/stableswap/raipool.py                                 |       14 |        8 |        2 |        0 |     38% |35-41, 44-46 |
| curvesim/pool\_data/\_\_init\_\_.py                                 |       12 |        3 |        0 |        0 |     75% |     41-44 |
| curvesim/pool\_data/cache.py                                        |       60 |       42 |       14 |        0 |     24% |34-50, 61-62, 68-69, 93-97, 100-116, 142-146, 149-157 |
| curvesim/pool\_data/metadata/\_\_init\_\_.py                        |       35 |        5 |        6 |        1 |     85% |50, 61-62, 67-68 |
| curvesim/pool\_data/metadata/base.py                                |       33 |        0 |        0 |        0 |    100% |           |
| curvesim/pool\_data/metadata/cryptoswap.py                          |       25 |        0 |        8 |        0 |    100% |           |
| curvesim/pool\_data/metadata/stableswap.py                          |       45 |        0 |       18 |        0 |    100% |           |
| curvesim/pool\_data/queries.py                                      |       16 |        3 |        4 |        0 |     85% |     46-50 |
| curvesim/price\_data/\_\_init\_\_.py                                |       10 |        4 |        6 |        1 |     44% |     51-55 |
| curvesim/price\_data/sources.py                                     |       19 |        8 |        2 |        0 |     52% |     19-30 |
| curvesim/sim/\_\_init\_\_.py                                        |       30 |       23 |       13 |        0 |     16% |138-151, 155-182 |
| curvesim/templates/\_\_init\_\_.py                                  |        7 |        0 |        0 |        0 |    100% |           |
| curvesim/templates/param\_samplers.py                               |       36 |        0 |       16 |        0 |    100% |           |
| curvesim/templates/price\_samplers.py                               |       10 |        0 |        2 |        0 |    100% |           |
| curvesim/templates/sim\_assets.py                                   |        8 |        0 |        0 |        0 |    100% |           |
| curvesim/templates/sim\_pool.py                                     |        6 |        0 |        0 |        0 |    100% |           |
| curvesim/templates/strategy.py                                      |       19 |        0 |        2 |        0 |    100% |           |
| curvesim/templates/trader.py                                        |       40 |        4 |       12 |        0 |     81% |20, 35, 39-40 |
| curvesim/utils.py                                                   |       50 |       12 |       21 |        8 |     69% |54, 57, 93, 105-114, 116->exit, 117, 140, 156 |
| curvesim/version.py                                                 |        7 |        0 |        0 |        0 |    100% |           |
|                                                           **TOTAL** | **3478** |  **800** |  **913** |   **89** | **73%** |           |


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