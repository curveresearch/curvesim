import pstats
from pstats import SortKey

p = pstats.Stats('output.txt')
p.sort_stats(SortKey.CUMULATIVE).print_stats(25)

p = pstats.Stats('output_gmp.txt')
p.sort_stats(SortKey.CUMULATIVE).print_stats(25)

