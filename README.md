# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/curveresearch/curvesim/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                                |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|-------------------------------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| curvesim/\_\_init\_\_.py                                            |        5 |        0 |        0 |        0 |    100% |           |
| curvesim/\_order\_book/\_\_init\_\_.py                              |       53 |       48 |       12 |        0 |      8% |52-100, 104-130 |
| curvesim/exceptions/\_\_init\_\_.py                                 |       20 |        0 |        0 |        0 |    100% |           |
| curvesim/iterators/\_\_init\_\_.py                                  |        0 |        0 |        0 |        0 |    100% |           |
| curvesim/iterators/param\_samplers/\_\_init\_\_.py                  |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/iterators/param\_samplers/parameterized\_pool\_iterator.py |       51 |        2 |       10 |        2 |     93% |   35, 116 |
| curvesim/iterators/param\_samplers/pool\_mixins.py                  |       41 |       11 |        8 |        0 |     69% |61, 71, 118-129 |
| curvesim/iterators/price\_samplers/\_\_init\_\_.py                  |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/iterators/price\_samplers/price\_volume.py                 |       24 |        1 |        4 |        0 |     96% |        98 |
| curvesim/logging.py                                                 |       45 |        0 |        6 |        1 |     98% |    94->96 |
| curvesim/metrics/\_\_init\_\_.py                                    |        6 |        0 |        2 |        0 |    100% |           |
| curvesim/metrics/base.py                                            |      123 |       11 |       31 |        4 |     90% |146-148, 221, 291-294, 342-343, 368->exit, 369, 371->376 |
| curvesim/metrics/metrics.py                                         |      181 |        0 |       22 |        0 |    100% |           |
| curvesim/metrics/results/\_\_init\_\_.py                            |        3 |        0 |        0 |        0 |    100% |           |
| curvesim/metrics/results/make\_results.py                           |       28 |        0 |       10 |        0 |    100% |           |
| curvesim/metrics/results/sim\_results.py                            |       35 |       12 |       12 |        3 |     55% |63-66, 92-94, 121, 129-132 |
| curvesim/metrics/state\_log/\_\_init\_\_.py                         |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/metrics/state\_log/log.py                                  |       28 |        0 |       10 |        0 |    100% |           |
| curvesim/metrics/state\_log/pool\_parameters.py                     |       17 |        0 |        6 |        0 |    100% |           |
| curvesim/metrics/state\_log/pool\_state.py                          |       12 |        0 |        2 |        0 |    100% |           |
| curvesim/network/\_\_init\_\_.py                                    |        0 |        0 |        0 |        0 |    100% |           |
| curvesim/network/coingecko.py                                       |       76 |        6 |       12 |        2 |     91% |62-66, 148 |
| curvesim/network/http.py                                            |       39 |        5 |        8 |        1 |     87% |42->45, 49-54 |
| curvesim/network/subgraph.py                                        |      136 |       55 |       48 |        2 |     56% |78, 113-144, 149, 213-229, 445-471, 504-528 |
| curvesim/network/utils.py                                           |       38 |        6 |        8 |        1 |     80% |41-42, 68-71 |
| curvesim/network/web3.py                                            |       70 |        3 |       16 |        4 |     90% |139->147, 143-144, 147->152, 176 |
| curvesim/overrides/\_\_init\_\_.py                                  |        9 |        3 |        4 |        1 |     54% |     40-42 |
| curvesim/pipelines/\_\_init\_\_.py                                  |       21 |        5 |       12 |        1 |     76% |     75-79 |
| curvesim/pipelines/common/\_\_init\_\_.py                           |       36 |        4 |       12 |        0 |     92% |     82-93 |
| curvesim/pipelines/simple/\_\_init\_\_.py                           |       25 |        0 |        2 |        1 |     96% |   99->104 |
| curvesim/pipelines/simple/strategy.py                               |       10 |        0 |        0 |        0 |    100% |           |
| curvesim/pipelines/simple/trader.py                                 |       24 |        0 |        8 |        0 |    100% |           |
| curvesim/pipelines/utils.py                                         |       46 |       36 |       14 |        0 |     17% |40-55, 59-72, 76-104, 108-110 |
| curvesim/pipelines/vol\_limited\_arb/\_\_init\_\_.py                |       38 |       25 |       12 |        0 |     26% |   112-155 |
| curvesim/pipelines/vol\_limited\_arb/strategy.py                    |       18 |        7 |        4 |        0 |     50% |28-29, 32-33, 37-39 |
| curvesim/pipelines/vol\_limited\_arb/trader.py                      |       49 |       40 |       20 |        0 |     13% |39-42, 74-144 |
| curvesim/plot/\_\_init\_\_.py                                       |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/plot/altair/\_\_init\_\_.py                                |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/plot/altair/chart\_properties.py                           |       35 |       25 |       14 |        0 |     20% |31-38, 61-66, 83-88, 130-142 |
| curvesim/plot/altair/make\_chart.py                                 |       30 |       23 |       10 |        0 |     18% |48-62, 94-117 |
| curvesim/plot/altair/results/\_\_init\_\_.py                        |        0 |        0 |        0 |        0 |    100% |           |
| curvesim/plot/altair/results/make\_page.py                          |       59 |       45 |       16 |        0 |     19% |40-46, 71-73, 98-107, 126-140, 165-170, 195-198, 223-235 |
| curvesim/plot/altair/results/preprocessing.py                       |       35 |       28 |       10 |        0 |     16% |32-35, 61-80, 101-103, 122, 141-148 |
| curvesim/plot/altair/results/result\_plotter.py                     |       25 |       14 |        0 |        0 |     44% |15-17, 25-30, 38-43, 53 |
| curvesim/plot/altair/results/result\_selectors.py                   |       40 |       32 |        6 |        0 |     17% |31-43, 65-75, 94-105, 127-137, 159-169, 188-190 |
| curvesim/plot/altair/results/tooltip.py                             |       10 |        8 |        4 |        0 |     14% |      6-16 |
| curvesim/plot/altair/selectors.py                                   |       32 |       24 |       10 |        0 |     19% |59-69, 97-109, 134-154, 179 |
| curvesim/plot/altair/styles.py                                      |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/plot/result\_plotter.py                                    |       16 |        9 |        8 |        0 |     29% |     53-63 |
| curvesim/pool/\_\_init\_\_.py                                       |       53 |       18 |       22 |        4 |     55% |108, 180-185, 220-232, 242-245 |
| curvesim/pool/base.py                                               |       50 |       21 |       18 |        4 |     49% |29-31, 36-38, 45, 52, 57-59, 66, 71-73, 80, 85-89 |
| curvesim/pool/cryptoswap/\_\_init\_\_.py                            |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/pool/cryptoswap/calcs/\_\_init\_\_.py                      |        0 |        0 |        0 |        0 |    100% |           |
| curvesim/pool/cryptoswap/calcs/factory\_2\_coin.py                  |      142 |       34 |       56 |       13 |     70% |40, 47-60, 67-68, 88, 90, 111-116, 138-139, 152, 162, 181, 183, 203-205, 230, 239, 242 |
| curvesim/pool/cryptoswap/calcs/tricrypto\_ng.py                     |      307 |       37 |      118 |       31 |     84% |62->66, 107, 109, 111, 113, 115, 127, 129-133, 141, 146, 152, 158, 166, 172, 178, 182, 224, 226, 243-245, 274-275, 288, 298, 310, 324, 417, 421, 501, 512, 519, 556, 583->586, 608 |
| curvesim/pool/cryptoswap/pool.py                                    |      469 |       62 |      166 |       26 |     84% |157, 164, 167, 172->175, 178, 188-190, 196, 201-205, 270, 322, 373->382, 378, 416->426, 431-454, 585->598, 589, 650, 695, 711->739, 715-730, 742-745, 928, 1009, 1026, 1038, 1060, 1097, 1101, 1121 |
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
| curvesim/pool\_data/cache.py                                        |       60 |       42 |       14 |        0 |     24% |35-51, 62-63, 69-70, 94-98, 101-117, 143-147, 150-158 |
| curvesim/pool\_data/metadata/\_\_init\_\_.py                        |       35 |        5 |        6 |        1 |     85% |51, 62-63, 68-69 |
| curvesim/pool\_data/metadata/base.py                                |       26 |        0 |        0 |        0 |    100% |           |
| curvesim/pool\_data/metadata/cryptoswap.py                          |       25 |        0 |        8 |        0 |    100% |           |
| curvesim/pool\_data/metadata/stableswap.py                          |       45 |        0 |       18 |        0 |    100% |           |
| curvesim/pool\_data/queries.py                                      |       16 |        3 |        4 |        0 |     85% |     46-50 |
| curvesim/price\_data/\_\_init\_\_.py                                |       10 |        4 |        6 |        1 |     44% |     59-63 |
| curvesim/price\_data/sources.py                                     |       19 |        8 |        2 |        0 |     52% |     19-30 |
| curvesim/sim/\_\_init\_\_.py                                        |       30 |       23 |       13 |        0 |     16% |138-151, 155-182 |
| curvesim/templates/\_\_init\_\_.py                                  |        7 |        0 |        0 |        0 |    100% |           |
| curvesim/templates/param\_samplers.py                               |       36 |        0 |       16 |        0 |    100% |           |
| curvesim/templates/price\_samplers.py                               |       10 |        0 |        2 |        0 |    100% |           |
| curvesim/templates/sim\_assets.py                                   |        8 |        0 |        0 |        0 |    100% |           |
| curvesim/templates/sim\_pool.py                                     |        6 |        0 |        0 |        0 |    100% |           |
| curvesim/templates/strategy.py                                      |       19 |        0 |        2 |        0 |    100% |           |
| curvesim/templates/trader.py                                        |       40 |        4 |       12 |        0 |     81% |20, 35, 39-40 |
| curvesim/tools/\_\_init\_\_.py                                      |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/tools/bonding\_curve.py                                    |       42 |       17 |       18 |        1 |     57% |72-76, 82-97 |
| curvesim/utils.py                                                   |       50 |       12 |       21 |        8 |     69% |54, 57, 93, 105-114, 116->exit, 117, 140, 156 |
| curvesim/version.py                                                 |        7 |        0 |        0 |        0 |    100% |           |
|                                                           **TOTAL** | **3842** |  **808** | **1089** |  **126** | **75%** |           |


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