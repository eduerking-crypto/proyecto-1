"""Tests del agente GENETIX: matemática de puntuaciones poligénicas."""
import math

import pytest

from agents.genetic_agent import Snp, compute_prs, dosage_from_genotype, simulate_genotypes


def make_snp(rsid="rs1", risk="A", other="G", orv=1.3, freq=0.3, gene="GENE1"):
    return Snp(rsid=rsid, gene=gene, disease="T2D", risk_allele=risk,
               other_allele=other, odds_ratio=orv, risk_allele_freq=freq)


class TestDosage:
    def test_homozygous_risk(self):
        assert dosage_from_genotype("AA", make_snp()) == 2

    def test_heterozygous(self):
        assert dosage_from_genotype("AG", make_snp()) == 1

    def test_homozygous_other(self):
        assert dosage_from_genotype("GG", make_snp()) == 0

    def test_single_allele_expanded(self):
        assert dosage_from_genotype("A", make_snp()) == 2

    def test_lowercase(self):
        assert dosage_from_genotype("ag", make_snp()) == 1

    def test_missing(self):
        assert dosage_from_genotype(None, make_snp()) is None

    def test_invalid_letters(self):
        assert dosage_from_genotype("XT", make_snp()) is None


class TestPRS:
    def test_zero_dosage_matches_population_mean(self):
        """Sin alelos de riesgo, RR ~ exp(0 - 0) = 1 respecto a la media... 
        con dosage 0 en todos, RR < 1 (por debajo de la media)."""
        snps = [make_snp()]
        res = compute_prs(snps, {"rs1": "GG"})
        assert res["rr"] < 1.0
        assert res["percentile"] < 50

    def test_high_dosage_raises_risk(self):
        snps = [make_snp()]
        res = compute_prs(snps, {"rs1": "AA"})
        assert res["rr"] > 1.0
        assert res["percentile"] > 50

    def test_rr_matches_manual_computation(self):
        snp = make_snp(orv=1.5, freq=0.25)
        res = compute_prs([snp], {"rs1": "AA"})
        expected = math.exp(math.log(1.5) * (2 - 2 * 0.25))
        assert res["rr"] == pytest.approx(expected, rel=1e-3)

    def test_missing_genotype_excluded(self):
        snps = [make_snp("rs1"), make_snp("rs2", freq=0.5)]
        res = compute_prs(snps, {"rs1": "AA"})
        assert res["n_used"] == 1
        assert res["n_total"] == 2

    def test_no_genotypes_returns_none(self):
        res = compute_prs([make_snp()], {})
        assert res["rr"] is None

    def test_percentile_monotonic_with_dosage(self):
        snps = [make_snp(orv=1.4, freq=0.2) for _ in range(3)]
        low = compute_prs(snps, {"rs1": "GG", "rs2": "GG", "rs3": "GG"})
        mid = compute_prs(snps, {"rs1": "AG", "rs2": "GG", "rs3": "GG"})
        high = compute_prs(snps, {"rs1": "AA", "rs2": "AA", "rs3": "AG"})
        assert low["percentile"] < mid["percentile"] < high["percentile"]

    def test_rr_capped(self):
        strong = [make_snp(f"rs{i}", orv=4.0, freq=0.3) for i in range(5)]
        res = compute_prs(strong, {f"rs{i}": "AA" for i in range(5)})
        assert res["rr"] <= 12.0

    def test_contributions_sorted(self):
        snps = [make_snp("rs1", orv=1.2, freq=0.5), make_snp("rs2", orv=1.8, freq=0.5)]
        res = compute_prs(snps, {"rs1": "AA", "rs2": "AA"})
        contribs = [abs(c["log_contribution"]) for c in res["contributions"]]
        assert contribs == sorted(contribs, reverse=True)


class TestSimulation:
    def test_hardy_weinberg_plausible(self):
        snps = [make_snp(f"rs{i}", freq=0.3) for i in range(200)]
        gts = simulate_genotypes(snps, seed=42)
        assert len(gts) == 200
        dosages = [dosage_from_genotype(gts[f"rs{i}"], snps[i]) for i in range(200)]
        mean_d = sum(dosages) / len(dosages)
        expected = 2 * 0.3
        assert abs(mean_d - expected) < 0.15

    def test_deterministic_with_seed(self):
        snps = [make_snp(f"rs{i}") for i in range(10)]
        a = simulate_genotypes(snps, seed=7)
        b = simulate_genotypes(snps, seed=7)
        assert a == b

    def test_enriched_has_more_risk_than_plain(self):
        from agents.genetic_agent import simulate_risk_enriched
        snps = [make_snp(f"rs{i}", freq=0.2) for i in range(50)]
        plain = simulate_genotypes(snps, seed=3)
        rich = simulate_risk_enriched(snps, seed=3)
        d_plain = sum(dosage_from_genotype(plain[f"rs{i}"], snps[i]) for i in range(50))
        d_rich = sum(dosage_from_genotype(rich[f"rs{i}"], snps[i]) for i in range(50))
        assert d_rich >= d_plain
