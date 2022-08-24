import pstats
from pstats import SortKey

p = pstats.Stats('output.txt')
p.sort_stats(SortKey.CUMULATIVE).print_stats(10)

