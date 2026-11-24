import numpy as np
from scipy.stats import hypergeom
from design_bounds import hypergeometric_count_interval,ratio_bounds


def test_census_reveals_exact_finite_count():
    for k in range(9):assert hypergeometric_count_interval(8,8,k)==(k,k)


def test_exact_count_interval_has_nominal_or_conservative_coverage():
    # Enumerate every possible draw in small finite populations, rather than
    # relying on Monte Carlo coverage or on the interval's own implementation.
    for N in range(2,9):
        for n in range(1,N+1):
            intervals=[hypergeometric_count_interval(N,n,k) for k in range(n+1)]
            for K in range(N+1):
                coverage=sum(hypergeom.pmf(k,N,K,n) for k,(lo,hi) in enumerate(intervals) if lo<=K<=hi)
                assert coverage>=.95-1e-12


def test_ratio_bounds_are_conservative_at_all_count_corners():
    lo,hi=ratio_bounds(2,10,3,20)
    for positive in [2,10]:
        for negative in [3,20]:assert lo<=positive/(positive+negative)<=hi
