import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alea import credibility, experience, normalize, pooling, report  # noqa: E402
from alea.reference import load_who_benin, mu_lookup  # noqa: E402


def test_reference_monotone_after_30():
    mu = mu_lookup(load_who_benin())
    for s in ("M", "F"):
        assert np.all(np.diff(mu[s][30:100]) > 0)
        assert 0 < mu[s][40] < 0.05


def test_exposure_single_policy():
    df = pd.DataFrame({"birth_date": [pd.Timestamp("1980-07-01")], "entry_date": [pd.Timestamp("2018-01-01")],
                       "exit_date": [pd.NaT], "exit_reason": [None], "sex": ["M"]})
    cells = experience.exposures(df)
    assert abs(cells["E"].sum() - 6.0) < 0.01  # fenêtre 2019-2024 complète
    assert cells["D"].sum() == 0


def test_death_counted_in_window():
    df = pd.DataFrame({"birth_date": [pd.Timestamp("1970-01-01")], "entry_date": [pd.Timestamp("2015-01-01")],
                       "exit_date": [pd.Timestamp("2021-06-30")], "exit_reason": ["death"], "sex": ["F"]})
    cells = experience.exposures(df)
    assert cells["D"].sum() == 1
    assert cells.loc[cells["D"] == 1, "age"].iloc[0] == 51


def test_two_digit_birth_years_century_fix():
    d = normalize.parse_dates(pd.Series(["03-04-55", "12-11-01"]), "%d-%m-%y", century_fix=True)
    assert list(d.dt.year) == [1955, 2001]


def test_credibility_shrinks_small_portfolios():
    own = pd.DataFrame({"sex": ["M"], "D": [12.0], "Ep": [8.0], "E": [1000.0]})
    big = credibility.apply_credibility(own.assign(D=1200.0, Ep=800.0), K=50)
    small = credibility.apply_credibility(own, K=50)
    assert small["Z"].iloc[0] < big["Z"].iloc[0]
    assert 1.0 < small["theta"].iloc[0] < 1.5 and abs(big["theta"].iloc[0] - 1.5) < 0.05


def test_band_of_covers_window():
    from alea import credibility as cr
    b = cr.band_of(pd.Series([20, 34, 35, 49, 50, 64, 65, 80]))
    assert list(b) == ["20-34", "20-34", "35-49", "35-49", "50-64", "50-64", "65-80", "65-80"]


def test_credibility_bands_recover_divergent_shape():
    bands = pd.DataFrame({"sex": ["M"] * 4, "band": ["20-34", "35-49", "50-64", "65-80"],
                          "D": [52.0, 68.0, 90.0, 120.0], "Ep": [75.0] * 4, "E": [7500.0] * 4})
    glob = pd.DataFrame({"sex": ["M"], "theta": [1.0]})
    out = credibility.apply_credibility_bands(bands, {b: 2.0 for b in bands["band"]}, glob)
    assert np.allclose(out["theta_retenu"], [0.7, 0.9, 1.2, 1.6], atol=0.05)
    market = {s: np.full(106, 0.01) for s in ("M", "F")}
    mu = credibility.credible_table_bands(out, market)
    assert abs(mu["M"][27] / 0.01 - 0.7) < 0.05   # milieu de la première bande
    assert abs(mu["M"][72] / 0.01 - 1.6) < 0.05   # milieu de la dernière
    assert mu["M"][45] < mu["M"][55]              # interpolation croissante entre bandes
    assert np.isclose(mu["F"], market["F"]).all()  # sans données femmes, table du marché inchangée


def test_credibility_bands_fallback_on_small_band():
    bands = pd.DataFrame({"sex": ["F", "F"], "band": ["20-34", "35-49"], "D": [1.0, 60.0],
                          "Ep": [5.0, 100.0], "E": [500.0, 1000.0]})
    glob = pd.DataFrame({"sex": ["F"], "theta": [0.8]})
    out = credibility.apply_credibility_bands(bands, {"20-34": 20.0, "35-49": 20.0}, glob)
    small = out[out["band"] == "20-34"]
    assert bool(small["repli"].iloc[0]) and abs(small["theta_retenu"].iloc[0] - 0.8) < 1e-9
    assert not bool(out[out["band"] == "35-49"]["repli"].iloc[0])


def test_mask_single_contributor_drops_unique_cells():
    a = pd.DataFrame({"assureur": ["A", "A", "A"], "sex": ["M", "M", "F"], "age": [30, 31, 30],
                      "E": [100.0, 50.0, 80.0], "D": [3.0, 1.0, 2.0]})
    b = pd.DataFrame({"assureur": ["B", "B"], "sex": ["M", "F"], "age": [30, 45],
                      "E": [120.0, 60.0], "D": [5.0, 1.0]})
    masked, info = pooling.mask_single_contributor([a, b])
    kept = pd.concat(masked, ignore_index=True)
    assert set(zip(kept["sex"], kept["age"])) == {("M", 30)}
    assert info["cellules_a_contributeur_unique"] == 3
    assert info["deces_supprimes"] == 4 and abs(info["expositions_supprimees (annees)"] - 190.0) < 1e-9


def test_guard_flags_untraced_numbers():
    facts = {"a": {"libellé": "x", "texte": "112 %"}, "b": {"libellé": "y", "texte": "2 450 FCFA"}}
    assert report.guard("La mortalité vaut 112 % et la prime 2 450 FCFA (IC à 95 %).", facts) == []
    assert report.guard("La mortalité vaut 118 %.", facts) == ["118"]
