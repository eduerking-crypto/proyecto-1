"""Tests del agente SIGMA: motor estadístico."""
import math

import pytest
from scipy import stats as sps

from agents import statistical_agent as sa


class TestSummary:
    def test_known_values(self):
        res = sa.summary([2, 4, 4, 4, 5, 5, 7, 9])
        assert res["n"] == 8
        assert res["mean"] == pytest.approx(5.0)
        assert res["sd"] == pytest.approx(2.13809, abs=1e-4)
        assert res["median"] == 4.5

    def test_ignores_invalid(self):
        res = sa.summary([1, 2, 3, None, float("nan")])
        assert res["n"] == 3

    def test_empty(self):
        assert "error" in sa.summary([])


class TestTTest:
    def test_matches_scipy_welch(self):
        a = [5.1, 4.9, 5.3, 5.0, 5.2, 5.4]
        b = [4.6, 4.4, 4.8, 4.5, 4.7]
        res = sa.ttest(a, b)
        ref = sps.ttest_ind(a, b, equal_var=False)
        assert res["statistic"] == pytest.approx(float(ref.statistic), abs=1e-3)
        assert res["p"] == pytest.approx(float(ref.pvalue), abs=1e-4)

    def test_paired(self):
        a = [1, 2, 3, 4, 5]
        b = [2, 3, 4, 5, 6]
        res = sa.ttest(a, b, paired=True)
        assert res["test"] == "t pareado"
        assert res["mean_diff"] == pytest.approx(-1.0)

    def test_too_small(self):
        assert "error" in sa.ttest([1], [2, 3])

    def test_apa_format(self):
        res = sa.ttest([1, 2, 3, 4, 5], [10, 11, 12, 13, 14])
        assert "t(" in res["apa"] and "p" in res["apa"] and "d =" in res["apa"]


class TestChisq:
    def test_known_association(self):
        res = sa.chisq([[20, 30], [50, 10]])
        assert res["p"] < 0.001
        assert res["cramers_v"] > 0.3

    def test_independence(self):
        res = sa.chisq([[25, 25], [25, 25]])
        assert res["p"] > 0.99

    def test_fisher_fallback_on_low_expected(self):
        res = sa.chisq([[3, 10], [1, 10]])
        assert res["warning_low_expected"] is True
        assert "fisher_exact_p" in res

    def test_rejects_bad_table(self):
        assert "error" in sa.chisq([[1]])


class TestOddsRatio:
    def test_perfect_association(self):
        res = sa.odds_ratio(100, 0, 0, 100)
        assert res["odds_ratio"] > 100

    def test_null(self):
        res = sa.odds_ratio(10, 10, 10, 10)
        assert res["odds_ratio"] == pytest.approx(1.0)
        lo, hi = res["ci95"]
        assert lo < 1 < hi

    def test_ci_symmetry_log_scale(self):
        res = sa.odds_ratio(30, 20, 45, 10)
        lo, hi = res["ci95"]
        assert lo < res["odds_ratio"] < hi
        midpoint = math.sqrt(lo * hi)
        assert midpoint == pytest.approx(res["odds_ratio"], rel=1e-2)

    def test_smoking_classic(self):
        """Estilo Doll & Hill: fumadores vs no fumadores."""
        res = sa.odds_ratio(a=688, b=650, c=21, d=59)
        assert res["odds_ratio"] > 2.5
        assert res["odds_ratio"] < 3.5


class TestCorrelation:
    def test_perfect_linear(self):
        x = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        res = sa.correlation(x, [v * 2 + 1 for v in x])
        assert res["r"] == pytest.approx(1.0)
        assert res["r_squared"] == pytest.approx(1.0)

    def test_inverse(self):
        res = sa.correlation([1, 2, 3, 4, 5], [10, 8, 6, 4, 2])
        assert res["r"] == pytest.approx(-1.0)

    def test_spearman_on_monotonic_nonlinear(self):
        res = sa.correlation([1, 2, 3, 4, 5, 6], [1, 4, 9, 16, 25, 36], method="spearman")
        assert res["r"] == pytest.approx(1.0)

    def test_zero_variance(self):
        assert "error" in sa.correlation([2, 2, 2], [1, 2, 3])


class TestAnova:
    def test_three_groups(self):
        groups = {"A": [10, 11, 12, 13], "B": [20, 21, 19, 22], "C": [30, 29, 31, 32]}
        res = sa.anova(groups)
        assert res["p"] < 0.001
        assert res["eta_squared"] > 0.9

    def test_needs_two_groups(self):
        assert "error" in sa.anova({"A": [1, 2, 3]})


class TestPower:
    def test_medium_effect(self):
        res = sa.power_two_means(0.5)
        assert 60 <= res["n_per_group_1"] <= 70

    def test_small_effect_needs_more(self):
        small = sa.power_two_means(0.2)
        medium = sa.power_two_means(0.5)
        assert small["n_per_group_1"] > medium["n_per_group_1"] * 4

    def test_invalid(self):
        assert "error" in sa.power_two_means(0)


class TestDataset:
    def test_autodetection(self):
        csv_text = ("edad,peso,grupo\n34,70.2,A\n45,82.1,B\n52,91.0,A\n"
                    "28,65.3,B\n61,88.7,A\n39,74.5,B")
        res = sa.analyze_dataset(csv_text, group_col="grupo", value_col="peso")
        assert res["n_rows"] == 6
        assert "edad" in res["numeric_columns"]
        assert "grupo" in res["categorical_columns"]
        assert res["group_test"] and "ttest" in res["group_test"]
        assert f"edad ~ peso" in res["correlations"]

    def test_empty(self):
        assert "error" in sa.analyze_dataset("")
