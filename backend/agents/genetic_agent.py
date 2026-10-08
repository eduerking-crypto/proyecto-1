"""Agent GENETIX — genetista molecular.

Calcula puntuaciones de riesgo poligénico (PRS) con la metodología
estándar de la literatura GWAS: suma ponderada de log(OR) por dosis
de alelo de riesgo, normalizada por expectativa y varianza bajo
equilibrio de Hardy-Weinberg.
"""
import math
import random
from dataclasses import dataclass

from scipy.stats import norm

DISCLAIMER = (
    "Puntuación poligénica con fines educativos y de investigación. Los OR provienen "
    "de GWAS publicados (mayoritariamente de ascendencia europea) y la transferibilidad "
    "entre ancestrias es limitada. No constituye diagnóstico clínico ni sustituye "
    "asesoría médica o consejería genética certificada."
)


@dataclass
class Snp:
    rsid: str
    gene: str
    disease: str
    risk_allele: str
    other_allele: str
    odds_ratio: float
    risk_allele_freq: float
    note: str = ""


def dosage_from_genotype(genotype: str | None, snp: Snp) -> int | None:
    """Devuelve 0, 1 o 2 alelos de riesgo a partir del genotipo informado."""
    if not genotype:
        return None
    gt = genotype.strip().upper().replace(" ", "")
    if len(gt) == 1:
        gt = gt * 2
    if len(gt) != 2:
        return None
    risk = snp.risk_allele.upper()
    other = snp.other_allele.upper()
    if set(gt) <= {risk}:
        return 2
    if set(gt) == {risk, other}:
        return 1
    if set(gt) <= {other}:
        return 0
    return None


def compute_prs(snps: list[Snp], genotypes: dict[str, str]) -> dict:
    """Puntuación poligénica normalizada frente a la media poblacional.

    rr = exp(suma_i log(OR_i) * (dosage_i - 2p_i))
    z  = (suma_i log(OR_i)*dosage_i - esperanza) / desviación
    donde esperanza = suma log(OR_i)*2p_i y var = suma log(OR_i)^2 * 2p_i(1-p_i)
    bajo equilibrio de Hardy-Weinberg.
    """
    weighted = 0.0
    expected = 0.0
    variance = 0.0
    contributions: list[dict] = []
    used = 0
    for snp in snps:
        w = math.log(snp.odds_ratio)
        p = min(max(snp.risk_allele_freq, 0.001), 0.999)
        expected += w * 2 * p
        variance += (w ** 2) * 2 * p * (1 - p)
        dosage = dosage_from_genotype(genotypes.get(snp.rsid), snp)
        if dosage is None:
            continue
        used += 1
        weighted += w * dosage
        contributions.append({
            "rsid": snp.rsid,
            "gene": snp.gene,
            "genotype": genotypes.get(snp.rsid, "").upper(),
            "dosage": dosage,
            "odds_ratio": snp.odds_ratio,
            "log_contribution": round(w * (dosage - 2 * p), 4),
            "note": snp.note,
        })
    if used == 0:
        return {"rr": None, "percentile": None, "z": None,
                "contributions": [], "n_used": 0, "n_total": len(snps)}
    z = (weighted - expected) / math.sqrt(max(variance, 1e-12))
    rr = math.exp(weighted - expected)
    rr = min(rr, 12.0)
    percentile = float(norm.cdf(z) * 100)
    contributions.sort(key=lambda c: abs(c["log_contribution"]), reverse=True)
    return {
        "rr": round(rr, 3),
        "percentile": round(percentile, 1),
        "z": round(z, 3),
        "contributions": contributions,
        "n_used": used,
        "n_total": len(snps),
    }


def simulate_genotypes(snps: list[Snp], seed: int | None = None) -> dict[str, str]:
    """Simula un genotipo plausible muestreando Hardy-Weinberg por SNP."""
    rng = random.Random(seed)
    genotypes: dict[str, str] = {}
    for snp in snps:
        p = min(max(snp.risk_allele_freq, 0.001), 0.999)
        q = 1 - p
        r = rng.random()
        if r < q * q:
            dosage = 0
        elif r < q * q + 2 * p * q:
            dosage = 1
        else:
            dosage = 2
        risk, other = snp.risk_allele.upper(), snp.other_allele.upper()
        genotypes[snp.rsid] = {0: other * 2, 1: f"{risk}{other}", 2: risk * 2}[dosage]
    return genotypes


def simulate_risk_enriched(snps: list[Snp], seed: int | None = None) -> dict[str, str]:
    """Perfil demo con sesgo hacia alelos de riesgo (para explorar el rango alto)."""
    rng = random.Random(seed)
    genotypes: dict[str, str] = {}
    for snp in snps:
        p = min(max(snp.risk_allele_freq, 0.001), 0.999)
        q = 1 - p
        r = rng.random() ** 0.45
        if r < q * q:
            dosage = 0
        elif r < q * q + 2 * p * q:
            dosage = 1
        else:
            dosage = 2
        risk, other = snp.risk_allele.upper(), snp.other_allele.upper()
        genotypes[snp.rsid] = {0: other * 2, 1: f"{risk}{other}", 2: risk * 2}[dosage]
    return genotypes
