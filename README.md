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
| curvesim/iterators/param\_samplers/pool\_mixins.py                  |       41 |       11 |       20 |        6 |     66% |18->17, 22->21, 39->38, 43->42, 60->59, 61, 64->63, 71, 118-129 |
| curvesim/iterators/price\_samplers/\_\_init\_\_.py                  |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/iterators/price\_samplers/price\_volume.py                 |       24 |        1 |        6 |        1 |     93% |71->70, 98 |
| curvesim/logging.py                                                 |       46 |        1 |       10 |        3 |     93% |30, 95->97, 103->102 |
| curvesim/metrics/\_\_init\_\_.py                                    |        6 |        0 |        2 |        0 |    100% |           |
| curvesim/metrics/base.py                                            |      123 |       11 |       63 |       20 |     83% |95->94, 108->107, 129->132, 130->129, 131->130, 132->131, 146-148, 152->154, 153->152, 154->153, 170->172, 171->170, 172->171, 221, 279->282, 280->279, 281->280, 282->281, 291-294, 342-343, 368->exit, 369, 371->376 |
| curvesim/metrics/metrics.py                                         |      181 |        0 |       36 |        7 |     97% |33->32, 150->149, 227->226, 294->293, 454->453, 534->533, 552->551 |
| curvesim/metrics/results/\_\_init\_\_.py                            |        3 |        0 |        0 |        0 |    100% |           |
| curvesim/metrics/results/make\_results.py                           |       28 |        0 |       10 |        0 |    100% |           |
| curvesim/metrics/results/sim\_results.py                            |       35 |       12 |       12 |        3 |     55% |63-66, 92-94, 121, 129-132 |
| curvesim/metrics/state\_log/\_\_init\_\_.py                         |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/metrics/state\_log/log.py                                  |       28 |        0 |       10 |        0 |    100% |           |
| curvesim/metrics/state\_log/pool\_parameters.py                     |       17 |        0 |        6 |        0 |    100% |           |
| curvesim/metrics/state\_log/pool\_state.py                          |       12 |        0 |        2 |        0 |    100% |           |
| curvesim/network/\_\_init\_\_.py                                    |        0 |        0 |        0 |        0 |    100% |           |
| curvesim/network/coingecko.py                                       |       76 |        6 |       12 |        2 |     91% |62-66, 148 |
| curvesim/network/http.py                                            |       39 |        5 |       20 |        7 |     80% |15->17, 16->15, 17->16, 37->39, 38->37, 39->38, 42->45, 49-54 |
| curvesim/network/subgraph.py                                        |      136 |       55 |       48 |        2 |     56% |78, 113-144, 149, 213-229, 445-471, 504-528 |
| curvesim/network/utils.py                                           |       38 |        6 |       10 |        2 |     79% |41-42, 61->60, 68-71 |
| curvesim/network/web3.py                                            |       70 |        3 |       16 |        4 |     90% |139->147, 143-144, 147->152, 176 |
| curvesim/overrides/\_\_init\_\_.py                                  |        9 |        3 |        4 |        1 |     54% |     40-42 |
| curvesim/pipelines/\_\_init\_\_.py                                  |       21 |        5 |       12 |        1 |     76% |     75-79 |
| curvesim/pipelines/common/\_\_init\_\_.py                           |       36 |        4 |       12 |        0 |     92% |     82-93 |
| curvesim/pipelines/simple/\_\_init\_\_.py                           |       25 |        0 |        2 |        1 |     96% |   99->104 |
| curvesim/pipelines/simple/strategy.py                               |       10 |        0 |        0 |        0 |    100% |           |
| curvesim/pipelines/simple/trader.py                                 |       24 |        0 |        8 |        0 |    100% |           |
| curvesim/pipelines/utils.py                                         |       46 |       36 |       14 |        0 |     17% |38-53, 57-70, 74-102, 106-108 |
| curvesim/pipelines/vol\_limited\_arb/\_\_init\_\_.py                |       38 |       25 |       12 |        0 |     26% |   112-155 |
| curvesim/pipelines/vol\_limited\_arb/strategy.py                    |       18 |        7 |        4 |        0 |     50% |28-29, 32-33, 37-39 |
| curvesim/pipelines/vol\_limited\_arb/trader.py                      |       49 |       40 |       20 |        0 |     13% |39-42, 74-144 |
| curvesim/plot/\_\_init\_\_.py                                       |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/plot/altair/\_\_init\_\_.py                                |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/plot/altair/chart\_properties.py                           |       35 |       25 |       14 |        0 |     20% |31-38, 61-66, 83-88, 130-142 |
| curvesim/plot/altair/make\_chart.py                                 |       30 |       23 |       10 |        0 |     18% |48-62, 94-117 |
| curvesim/plot/altair/results/\_\_init\_\_.py                        |        0 |        0 |        0 |        0 |    100% |           |
| curvesim/plot/altair/results/make\_page.py                          |       60 |       46 |       18 |        0 |     18% |40-46, 71-73, 98-109, 128-142, 167-172, 197-200, 225-237 |
| curvesim/plot/altair/results/preprocessing.py                       |       37 |       30 |       12 |        0 |     14% |32-35, 61-80, 101-103, 122-125, 144-151 |
| curvesim/plot/altair/results/result\_plotter.py                     |       25 |       14 |        2 |        1 |     44% |15-17, 25-30, 38-43, 52->51, 53 |
| curvesim/plot/altair/results/result\_selectors.py                   |       40 |       32 |        6 |        0 |     17% |31-43, 65-75, 94-105, 127-137, 159-169, 188-190 |
| curvesim/plot/altair/results/tooltip.py                             |       11 |        9 |        4 |        0 |     13% |      6-18 |
| curvesim/plot/altair/selectors.py                                   |       32 |       24 |       10 |        0 |     19% |59-69, 97-109, 134-154, 179 |
| curvesim/plot/altair/styles.py                                      |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/plot/result\_plotter.py                                    |       16 |        9 |        8 |        0 |     29% |     53-63 |
| curvesim/pool/\_\_init\_\_.py                                       |       53 |       18 |       22 |        4 |     55% |108, 182-187, 222-234, 244-247 |
| curvesim/pool/base.py                                               |       50 |       21 |       34 |       12 |     49% |27->26, 29-31, 34->33, 36-38, 41->40, 45, 48->47, 52, 55->54, 57-59, 62->61, 66, 69->68, 71-73, 76->75, 80, 85-89 |
| curvesim/pool/cryptoswap/\_\_init\_\_.py                            |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/pool/cryptoswap/calcs/\_\_init\_\_.py                      |       68 |        6 |       28 |        6 |     88% |39, 58, 70, 92, 129, 133 |
| curvesim/pool/cryptoswap/calcs/factory\_2\_coin.py                  |      129 |       13 |       46 |       12 |     86% |40, 60, 86, 88, 130-131, 144, 154, 173, 175, 218, 227, 230 |
| curvesim/pool/cryptoswap/calcs/tricrypto\_ng.py                     |      303 |       35 |      116 |       31 |     84% |68->72, 113, 115, 117, 119, 121, 123, 133, 135-139, 147, 152, 158, 164, 172, 178, 184, 188, 230, 232, 276-277, 290, 300, 312, 326, 419, 423, 504, 515, 522, 559, 586->589, 611 |
| curvesim/pool/cryptoswap/pool.py                                    |      409 |       55 |      132 |       19 |     84% |161, 168, 171, 176->179, 182, 191-193, 199, 204-208, 273, 325, 376->385, 381, 419->429, 434-457, 624->637, 628, 684, 730, 746->774, 750-765, 777-780, 965 |
| curvesim/pool/sim\_interface/\_\_init\_\_.py                        |        5 |        0 |        0 |        0 |    100% |           |
| curvesim/pool/sim\_interface/asset\_indices.py                      |       22 |        1 |       16 |        5 |     84% |32->31, 36->38, 37->36, 38->37, 60 |
| curvesim/pool/sim\_interface/cryptoswap.py                          |       41 |       17 |       30 |       13 |     52% |18-23, 27->30, 28->27, 29->28, 30->29, 32, 34->36, 35->34, 36->35, 38, 41->40, 67, 70->69, 96-98, 121-127, 129->132, 130->129, 131->130, 132->131, 133 |
| curvesim/pool/sim\_interface/metapool.py                            |       86 |        3 |       50 |       16 |     86% |25, 27->30, 28->27, 29->28, 30->29, 42->44, 43->42, 44->43, 53->52, 65->64, 93, 96, 130->133, 131->130, 132->131, 133->132 |
| curvesim/pool/sim\_interface/pool.py                                |       42 |        1 |       30 |       14 |     79% |17, 19->22, 20->19, 21->20, 22->21, 26->28, 27->26, 28->27, 33->32, 38->37, 55->58, 56->55, 57->56, 58->57 |
| curvesim/pool/sim\_interface/raipool.py                             |       10 |        2 |        0 |        0 |     80% |     33-34 |
| curvesim/pool/snapshot.py                                           |       55 |        0 |        8 |        3 |     95% |38->37, 106->105, 138->137 |
| curvesim/pool/stableswap/\_\_init\_\_.py                            |        4 |        0 |        0 |        0 |    100% |           |
| curvesim/pool/stableswap/metapool.py                                |      278 |       10 |       84 |        8 |     95% |84, 349, 485->497, 504, 558->557, 655-657, 689, 775, 796, 853 |
| curvesim/pool/stableswap/pool.py                                    |      198 |        2 |       52 |        2 |     98% |389->401, 408, 569 |
| curvesim/pool/stableswap/raipool.py                                 |       14 |        8 |        2 |        0 |     38% |35-41, 44-46 |
| curvesim/pool\_data/\_\_init\_\_.py                                 |       12 |        3 |        0 |        0 |     75% |     41-44 |
| curvesim/pool\_data/cache.py                                        |       60 |       42 |       18 |        2 |     26% |35-51, 62-63, 69-70, 73->72, 94-98, 101-117, 120->119, 143-147, 150-158 |
| curvesim/pool\_data/metadata/\_\_init\_\_.py                        |       35 |        5 |        6 |        1 |     85% |51, 62-63, 68-69 |
| curvesim/pool\_data/metadata/base.py                                |       26 |        0 |        8 |        4 |     88% |160->159, 164->163, 168->167, 172->171 |
| curvesim/pool\_data/metadata/cryptoswap.py                          |       25 |        0 |       14 |        3 |     92% |45->44, 49->48, 53->52 |
| curvesim/pool\_data/metadata/stableswap.py                          |       45 |        0 |       24 |        3 |     96% |49->48, 60->59, 71->70 |
| curvesim/pool\_data/queries.py                                      |       16 |        3 |        4 |        0 |     85% |     46-50 |
| curvesim/price\_data/\_\_init\_\_.py                                |       10 |        4 |        6 |        1 |     44% |     59-63 |
| curvesim/price\_data/sources.py                                     |       19 |        8 |        2 |        0 |     52% |     60-71 |
| curvesim/sim/\_\_init\_\_.py                                        |       30 |       23 |       13 |        0 |     16% |138-151, 155-182 |
| curvesim/templates/\_\_init\_\_.py                                  |        7 |        0 |        0 |        0 |    100% |           |
| curvesim/templates/param\_samplers.py                               |       36 |        0 |       18 |        1 |     98% |    56->55 |
| curvesim/templates/price\_samplers.py                               |       10 |        0 |        2 |        0 |    100% |           |
| curvesim/templates/sim\_assets.py                                   |        8 |        0 |        0 |        0 |    100% |           |
| curvesim/templates/sim\_pool.py                                     |        6 |        0 |        0 |        0 |    100% |           |
| curvesim/templates/strategy.py                                      |       19 |        0 |        2 |        0 |    100% |           |
| curvesim/templates/trader.py                                        |       40 |        4 |       14 |        1 |     80% |20, 35, 39-40, 43->42 |
| curvesim/tools/\_\_init\_\_.py                                      |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/tools/bonding\_curve.py                                    |       42 |       17 |       18 |        1 |     57% |72-76, 82-97 |
| curvesim/utils.py                                                   |       50 |       12 |       21 |        8 |     69% |54, 57, 93, 105-114, 116->exit, 117, 140, 156 |
| curvesim/version.py                                                 |        7 |        0 |        0 |        0 |    100% |           |
|                                                           **TOTAL** | **3880** |  **806** | **1297** |  **233** | **75%** |           |


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