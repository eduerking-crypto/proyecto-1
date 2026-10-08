"""Tests de integración de la API GENOMIND."""
import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from database import init_db

init_db()
main = importlib.import_module("main")
client = TestClient(main.app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["diseases"] == 11
    assert body["snps"] >= 70
    assert body["foods"] >= 70
    assert body["regions"] >= 25


def test_agents_meta():
    r = client.get("/api/meta/agents")
    assert r.status_code == 200
    agents = {a["id"] for a in r.json()}
    assert agents == {"genetix", "sigma", "vita", "terra", "nutrix"}


def test_diseases():
    r = client.get("/api/diseases")
    assert r.status_code == 200
    diseases = r.json()
    assert len(diseases) == 11
    codes = {d["code"] for d in diseases}
    assert {"T2D", "CAD", "ALZ", "LUNG"} <= codes
    t2d = next(d for d in diseases if d["code"] == "T2D")
    assert t2d["baseline_risk"] > 0


def test_disease_snps():
    r = client.get("/api/diseases/T2D/snps")
    assert r.status_code == 200
    snps = r.json()
    assert len(snps) == 10
    rsids = {s["rsid"] for s in snps}
    assert "rs7903146" in rsids
    assert "rs9939609" in rsids

    r404 = client.get("/api/diseases/XXX/snps")
    assert r404.status_code == 404


def test_batch_prs_with_genotypes():
    r = client.post("/api/analysis/polygenic/batch", json={
        "diseases": ["T2D"],
        "genotypes": {"rs7903146": "TT", "rs9939609": "AA", "rs5219": "TT",
                      "rs10811661": "CC", "rs4402960": "TT", "rs13266634": "CC",
                      "rs1111875": "CC", "rs2237892": "CC", "rs1801282": "CC",
                      "rs7961581": "TT"},
    })
    assert r.status_code == 200
    result = r.json()["results"][0]
    assert result["code"] == "T2D"
    assert result["rr"] > 1.5
    assert result["percentile"] > 80
    assert result["abs_risk"] > result["baseline_risk"]
    assert "TCF7L2" in {c["gene"] for c in result["contributions"]}


def test_batch_prs_simulated():
    r = client.post("/api/analysis/polygenic/batch", json={
        "diseases": ["CAD"], "simulated": True, "seed": 42})
    assert r.status_code == 200
    assert len(r.json()["results"]) == 1
    assert r.json()["genotypes_used"]


def test_gene_environment_smoking_deltas_lung():
    """Fumador vs no fumador con el mismo genotipo: el riesgo combinado de pulmón debe multiplicarse."""
    def run(smoking):
        r = client.post("/api/analysis/gene-environment", json={
            "genotypes": {"rs16969968": "AA", "rs1051730": "TT", "rs8034191": "CC",
                          "rs401681": "CC", "rs2736100": "GG"},
            "lifestyle": {"smoking": smoking, "activity": "sedentario",
                          "diet": "mixta", "alcohol": "ninguno", "sleep": "adecuado",
                          "stress": "bajo", "servings_fv": 2},
        })
        assert r.status_code == 200
        return next(d for d in r.json()["diseases"] if d["code"] == "LUNG")

    never = run("nunca")
    smoker = run("fumador")
    assert smoker["rr_combined"] > never["rr_combined"] * 10
    assert never["abs_optimized"] <= smoker["abs_optimized"] + 1e-9
    assert any(i["id"] == "chrna5_smoke" for i in never["interactions"])


def test_gene_environment_lifestyle_scores():
    r = client.post("/api/analysis/gene-environment", json={
        "genotypes": {}, "simulated": True, "seed": 1,
        "lifestyle": {"smoking": "nunca", "activity": "intenso",
                      "diet": "mediterranea", "alcohol": "ninguno",
                      "sleep": "adecuado", "stress": "bajo", "servings_fv": 6},
    })
    assert r.status_code == 200
    body = r.json()
    scores = body["lifestyle_scores"]
    assert scores["tabaquismo"] == 100
    assert scores["dieta"] == 95
    assert scores["frutas/verduras"] == 96
    assert body["diseases"]
    for d in body["diseases"]:
        assert d["abs_optimized"] <= d["abs_combined"] + 1e-9


def test_foods_search_and_compare():
    r = client.get("/api/foods", params={"q": "frijol"})
    assert r.status_code == 200
    foods = r.json()
    assert foods and foods[0]["name"] == "Frijol negro"
    assert foods[0]["health_score"] > 70

    ids = [f["id"] for f in client.get("/api/foods").json()[:3]]
    r2 = client.post("/api/foods/compare", json={"ids": ids})
    assert r2.status_code == 200
    body = r2.json()
    assert len(body["foods"]) == 3
    assert "winner" in body and "cheapest" in body


def test_basket_covers_targets():
    r = client.post("/api/nutrition/basket", json={"max_cost": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["estimated_daily"]["protein_g"] >= 30
    assert body["coverage"]["protein_pct"] > 50
    names = " ".join(i["name"].lower() for i in body["items"])
    assert any(staple in names for staple in ("frijol", "lenteja", "huevo", "sardina", "soja"))


def test_regions():
    r = client.get("/api/regions")
    assert r.status_code == 200
    regions = {x["id"]: x for x in r.json()}
    assert "MX-CDMX" in regions
    assert regions["IN-DEL"]["pm25"] > 80
    r2 = client.get("/api/regions", params={"country": "Colombia"})
    assert all("Colombia" in x["country"] for x in r2.json())


def test_stats_endpoints():
    r = client.post("/api/stats/ttest", json={
        "a": [5.1, 4.9, 5.3, 5.0, 5.2], "b": [4.6, 4.4, 4.8, 4.5]})
    assert r.status_code == 200 and "apa" in r.json()

    r = client.post("/api/stats/chisq", json={"table": [[20, 30], [50, 10]]})
    assert r.json()["p"] < 0.001

    r = client.post("/api/stats/or", json={"a": 688, "b": 650, "c": 21, "d": 59})
    assert 2.5 < r.json()["odds_ratio"] < 3.5

    r = client.post("/api/stats/power", json={"effect_d": 0.5})
    assert r.json()["n_per_group_1"] >= 60


def test_profile_crud():
    r = client.post("/api/profiles", json={
        "name": "Test", "genotypes": {"rs7903146": "CT"},
        "lifestyle": {"smoking": "nunca"}})
    assert r.status_code == 200
    pid = r.json()["id"]

    r2 = client.get(f"/api/profiles/{pid}")
    assert r2.status_code == 200
    assert r2.json()["genotypes"] == {"rs7903146": "CT"}

    r3 = client.delete(f"/api/profiles/{pid}")
    assert r3.json()["deleted"] is True
    assert client.get(f"/api/profiles/{pid}").status_code == 404


def test_frontend_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "GENOMIND" in r.text
