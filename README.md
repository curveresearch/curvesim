# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/curveresearch/curvesim/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                                |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|-------------------------------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| curvesim/\_\_init\_\_.py                                            |        5 |        0 |        0 |        0 |    100% |           |
| curvesim/\_order\_book/\_\_init\_\_.py                              |       53 |       48 |       12 |        0 |      8% |53-101, 105-131 |
| curvesim/constants.py                                               |       15 |        0 |        0 |        0 |    100% |           |
| curvesim/exceptions/\_\_init\_\_.py                                 |       23 |        0 |        0 |        0 |    100% |           |
| curvesim/iterators/\_\_init\_\_.py                                  |        0 |        0 |        0 |        0 |    100% |           |
| curvesim/iterators/param\_samplers/\_\_init\_\_.py                  |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/iterators/param\_samplers/parameterized\_pool\_iterator.py |       51 |        1 |       10 |        1 |     97% |        40 |
| curvesim/iterators/param\_samplers/pool\_mixins.py                  |       51 |        0 |       16 |        6 |     91% |23->22, 27->26, 44->43, 48->47, 65->64, 69->68 |
| curvesim/iterators/price\_samplers/\_\_init\_\_.py                  |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/iterators/price\_samplers/price\_volume.py                 |       23 |        0 |        6 |        1 |     97% |    73->72 |
| curvesim/logging.py                                                 |       47 |        1 |       10 |        3 |     93% |31, 96->98, 104->103 |
| curvesim/metrics/\_\_init\_\_.py                                    |        6 |        0 |        2 |        0 |    100% |           |
| curvesim/metrics/base.py                                            |      128 |        6 |       69 |       19 |     87% |95->94, 108->107, 129->132, 130->129, 131->130, 132->131, 152->154, 153->152, 154->153, 170->172, 171->170, 172->171, 221, 279->282, 280->279, 281->280, 282->281, 291-294, 379->exit, 380 |
| curvesim/metrics/metrics.py                                         |      215 |       25 |       56 |       15 |     84% |39->38, 155->157, 156->155, 157->156, 267->269, 268->267, 269->268, 336->338, 337->336, 338->337, 527->529, 528->527, 529->528, 569-575, 582-588, 594-607, 610->609, 615-621, 628->627 |
| curvesim/metrics/results/\_\_init\_\_.py                            |        3 |        0 |        0 |        0 |    100% |           |
| curvesim/metrics/results/make\_results.py                           |       28 |        0 |       10 |        0 |    100% |           |
| curvesim/metrics/results/sim\_results.py                            |       35 |       12 |       12 |        3 |     55% |63-66, 92-94, 121, 129-132 |
| curvesim/metrics/state\_log/\_\_init\_\_.py                         |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/metrics/state\_log/log.py                                  |       32 |        0 |       14 |        2 |     96% |35->34, 54->53 |
| curvesim/metrics/state\_log/pool\_parameters.py                     |       28 |        0 |       10 |        0 |    100% |           |
| curvesim/metrics/state\_log/pool\_state.py                          |       18 |        0 |        2 |        0 |    100% |           |
| curvesim/network/\_\_init\_\_.py                                    |        0 |        0 |        0 |        0 |    100% |           |
| curvesim/network/coingecko.py                                       |       80 |        6 |       12 |        2 |     91% |63-67, 153 |
| curvesim/network/curve\_prices.py                                   |       34 |        3 |        4 |        2 |     87% |47-48, 118->121, 122 |
| curvesim/network/http.py                                            |       39 |        5 |       20 |        7 |     80% |15->17, 16->15, 17->16, 37->39, 38->37, 39->38, 42->45, 49-54 |
| curvesim/network/subgraph.py                                        |      124 |       48 |       48 |        6 |     59% |59-62, 94, 129-160, 321, 323, 325, 328->331, 385-411, 444-468 |
| curvesim/network/utils.py                                           |       22 |        6 |        6 |        2 |     64% |21-22, 41->40, 48-51 |
| curvesim/network/web3.py                                            |       70 |        5 |       16 |        5 |     86% |62-63, 139->147, 143-144, 147->152, 176 |
| curvesim/overrides/\_\_init\_\_.py                                  |        9 |        3 |        4 |        1 |     54% |     40-42 |
| curvesim/pipelines/\_\_init\_\_.py                                  |       21 |        5 |       12 |        1 |     76% |     75-79 |
| curvesim/pipelines/common/\_\_init\_\_.py                           |       42 |        4 |       10 |        0 |     92% |     78-89 |
| curvesim/pipelines/simple/\_\_init\_\_.py                           |       20 |        0 |        0 |        0 |    100% |           |
| curvesim/pipelines/simple/strategy.py                               |       11 |        0 |        0 |        0 |    100% |           |
| curvesim/pipelines/simple/trader.py                                 |       26 |        0 |       10 |        0 |    100% |           |
| curvesim/pipelines/vol\_limited\_arb/\_\_init\_\_.py                |       29 |       17 |        4 |        0 |     36% |    90-115 |
| curvesim/pipelines/vol\_limited\_arb/strategy.py                    |       22 |       10 |        6 |        0 |     43% |30-31, 34-35, 39-46 |
| curvesim/pipelines/vol\_limited\_arb/trader.py                      |       81 |       57 |       34 |        0 |     24% |41-44, 76-133, 159-160, 168-174, 204-216 |
| curvesim/plot/\_\_init\_\_.py                                       |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/plot/altair/\_\_init\_\_.py                                |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/plot/altair/chart\_properties.py                           |       35 |       25 |       14 |        0 |     20% |31-38, 61-66, 83-88, 130-142 |
| curvesim/plot/altair/make\_chart.py                                 |       30 |       23 |       10 |        0 |     18% |48-62, 94-117 |
| curvesim/plot/altair/results/\_\_init\_\_.py                        |        0 |        0 |        0 |        0 |    100% |           |
| curvesim/plot/altair/results/make\_page.py                          |       60 |       46 |       18 |        0 |     18% |40-46, 71-73, 98-109, 128-142, 167-172, 197-200, 225-237 |
| curvesim/plot/altair/results/preprocessing.py                       |       40 |       33 |       12 |        0 |     13% |32-38, 64-83, 104-106, 125-128, 147-154 |
| curvesim/plot/altair/results/result\_plotter.py                     |       25 |       14 |        2 |        1 |     44% |15-17, 25-30, 38-43, 52->51, 53 |
| curvesim/plot/altair/results/result\_selectors.py                   |       40 |       32 |        6 |        0 |     17% |31-43, 65-75, 94-105, 127-137, 159-169, 188-190 |
| curvesim/plot/altair/results/tooltip.py                             |       11 |        9 |        4 |        0 |     13% |      6-18 |
| curvesim/plot/altair/selectors.py                                   |       32 |       24 |       10 |        0 |     19% |59-69, 97-109, 134-154, 179 |
| curvesim/plot/altair/styles.py                                      |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/plot/result\_plotter.py                                    |       16 |        9 |        8 |        0 |     29% |     53-63 |
| curvesim/pool/\_\_init\_\_.py                                       |       67 |       13 |       28 |        9 |     73% |111, 180, 184-185, 188, 259, 263-264, 267, 278-281, 297->306 |
| curvesim/pool/base.py                                               |       51 |       21 |       34 |       12 |     49% |29->28, 31-33, 36->35, 38-40, 43->42, 47, 50->49, 54, 57->56, 59-61, 64->63, 68, 71->70, 73-75, 78->77, 82, 87-91 |
| curvesim/pool/cryptoswap/\_\_init\_\_.py                            |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/pool/cryptoswap/calcs/\_\_init\_\_.py                      |       68 |        7 |       28 |        7 |     85% |39, 58, 76, 100, 118, 137, 141 |
| curvesim/pool/cryptoswap/calcs/factory\_2\_coin.py                  |      126 |       13 |       46 |       12 |     85% |40, 60, 102, 104, 142-143, 156, 166, 185, 187, 230, 239, 242 |
| curvesim/pool/cryptoswap/calcs/tricrypto\_ng.py                     |      311 |       36 |      122 |       33 |     84% |68->72, 114, 116, 118, 120, 122, 134, 136, 138-142, 150, 152, 157, 163, 167, 173, 181, 187, 193, 197, 239, 241, 285-286, 299, 309, 321, 441, 445, 523, 534, 541, 578, 605->608, 630 |
| curvesim/pool/cryptoswap/pool.py                                    |      475 |       32 |      160 |       22 |     91% |169, 176, 179, 184->187, 190, 204, 341, 394->403, 399, 474->481, 650->663, 654, 710, 757, 776-791, 803-807, 862->865, 999-1001, 1019->1029, 1083, 1108, 1253->1257 |
| curvesim/pool/sim\_interface/\_\_init\_\_.py                        |        5 |        0 |        0 |        0 |    100% |           |
| curvesim/pool/sim\_interface/asset\_indices.py                      |       22 |        1 |       16 |        5 |     84% |32->31, 36->38, 37->36, 38->37, 60 |
| curvesim/pool/sim\_interface/cryptoswap.py                          |       83 |        2 |       50 |       19 |     84% |29, 33->36, 34->33, 35->34, 36->35, 40->42, 41->40, 42->41, 44, 47->46, 77->76, 108->107, 139->138, 160->159, 174->173, 191->195, 217->220, 218->217, 219->218, 220->219 |
| curvesim/pool/sim\_interface/metapool.py                            |       90 |       20 |       54 |       18 |     68% |30, 32->35, 33->32, 34->33, 35->34, 47->49, 48->47, 49->48, 51-55, 58->57, 91-93, 96->95, 128-129, 135-151, 154->153, 202->201, 218->221, 219->218, 220->219, 221->220 |
| curvesim/pool/sim\_interface/pool.py                                |       46 |        2 |       34 |       16 |     78% |22, 24->27, 25->24, 26->25, 27->26, 31->33, 32->31, 33->32, 35, 38->37, 69->68, 100->99, 129->128, 145->148, 146->145, 147->146, 148->147 |
| curvesim/pool/sim\_interface/raipool.py                             |       10 |        2 |        0 |        0 |     80% |     34-35 |
| curvesim/pool/snapshot.py                                           |       89 |        0 |       10 |        4 |     96% |76->75, 107->106, 139->138, 191->190 |
| curvesim/pool/stableswap/\_\_init\_\_.py                            |        4 |        0 |        0 |        0 |    100% |           |
| curvesim/pool/stableswap/metapool.py                                |      291 |       12 |       90 |       10 |     94% |88, 99, 371, 507->519, 526, 580->579, 677-679, 711, 797, 818, 875-877 |
| curvesim/pool/stableswap/pool.py                                    |      246 |        5 |       66 |        5 |     97% |84, 410->422, 429, 554, 669, 719 |
| curvesim/pool/stableswap/raipool.py                                 |       14 |        8 |        2 |        0 |     38% |35-41, 44-46 |
| curvesim/pool\_data/\_\_init\_\_.py                                 |        3 |        0 |        0 |        0 |    100% |           |
| curvesim/pool\_data/metadata/\_\_init\_\_.py                        |       35 |        5 |        6 |        1 |     85% |55, 66-67, 72-73 |
| curvesim/pool\_data/metadata/base.py                                |       26 |        0 |        8 |        4 |     88% |152->151, 156->155, 160->159, 164->163 |
| curvesim/pool\_data/metadata/cryptoswap.py                          |       25 |        0 |       12 |        3 |     92% |46->45, 50->49, 54->53 |
| curvesim/pool\_data/metadata/stableswap.py                          |       43 |        0 |       20 |        3 |     95% |51->50, 62->61, 73->72 |
| curvesim/pool\_data/queries/\_\_init\_\_.py                         |        0 |        0 |        0 |        0 |    100% |           |
| curvesim/pool\_data/queries/metadata.py                             |       26 |        3 |        4 |        0 |     90% |     54-58 |
| curvesim/pool\_data/queries/pool\_volume.py                         |       56 |        1 |       10 |        2 |     95% |93, 124->126 |
| curvesim/price\_data/\_\_init\_\_.py                                |       10 |        4 |        6 |        1 |     44% |     59-63 |
| curvesim/price\_data/sources.py                                     |        8 |        0 |        0 |        0 |    100% |           |
| curvesim/sim/\_\_init\_\_.py                                        |       29 |       22 |       13 |        0 |     17% |140-152, 156-193 |
| curvesim/templates/\_\_init\_\_.py                                  |        8 |        0 |        0 |        0 |    100% |           |
| curvesim/templates/log.py                                           |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/templates/param\_samplers.py                               |       36 |        0 |       18 |        1 |     98% |    56->55 |
| curvesim/templates/price\_samplers.py                               |       10 |        0 |        2 |        0 |    100% |           |
| curvesim/templates/sim\_assets.py                                   |        8 |        0 |        0 |        0 |    100% |           |
| curvesim/templates/sim\_pool.py                                     |        8 |        0 |        0 |        0 |    100% |           |
| curvesim/templates/strategy.py                                      |       23 |        0 |        2 |        0 |    100% |           |
| curvesim/templates/trader.py                                        |       47 |        3 |       16 |        1 |     87% |46, 50-51, 54->53 |
| curvesim/tools/\_\_init\_\_.py                                      |        2 |        0 |        0 |        0 |    100% |           |
| curvesim/tools/bonding\_curve.py                                    |       76 |       19 |       28 |        5 |     69% |70->91, 79->91, 89, 119-123, 145->149, 161-177 |
| curvesim/utils/\_\_init\_\_.py                                      |       37 |        3 |        8 |        3 |     87% |68, 71, 107 |
| curvesim/utils/address.py                                           |       12 |        3 |        2 |        0 |     64% |     47-50 |
| curvesim/utils/decorators.py                                        |       25 |        8 |       13 |        4 |     63% |41, 53-62, 64->exit, 65 |
| curvesim/version.py                                                 |        7 |        0 |        0 |        0 |    100% |           |
|                                                           **TOTAL** | **4254** |  **722** | **1407** |  **277** | **78%** |           |


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