import numpy as np
import pandas as pd

from analyze import cluster_risk_difference, compare


def test_small_contingency_table_orientation_and_fisher():
    # Table exposed: 4 test additions / 5; unexposed: 1 / 5.
    # Fisher's two-sided p for [[4,1],[1,4]] is 0.2063492063.
    d = pd.DataFrame({"repo_name": ["a"]*5 + ["b"]*5,
                      "exposure": [1]*5 + [0]*5,
                      "outcome": [1,1,1,1,0,1,0,0,0,0]})
    rates, effect = compare(d, "exposure", "outcome", "synthetic")
    assert effect["test"] == "Fisher exact"
    assert np.isclose(effect["p_value"], .2063492063492064)
    assert np.isclose(effect["risk_difference"], .6)
    assert effect["odds_ratio"] > 1
    assert rates[1]["rate"] == .8


def test_constant_exposure_does_not_invent_an_effect():
    d = pd.DataFrame({"repo_name": ["a", "b"], "exposure": [1,1], "outcome": [1,0]})
    _, effect = compare(d, "exposure", "outcome", "synthetic")
    assert effect["status"] == "insufficient predictor or outcome variation"
    lo, hi, valid = cluster_risk_difference(d, "exposure", "outcome", repetitions=20)
    assert np.isnan(lo) and np.isnan(hi) and valid == 0
