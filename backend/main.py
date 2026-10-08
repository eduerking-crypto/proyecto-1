"""GENOMIND API — Inteligencia genómica abierta para la prevención de ENT.

Servidor FastAPI que expone los cuatro agentes científicos:
GENETIX (genetista), SIGMA (bioestadístico), VITA (estilo de vida)
y TERRA (ambiental), con datos en SQLite y frontend estático servido
en la raíz.
"""
import json
import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agents import genetic_agent, lifestyle_agent, nutrition_agent, statistical_agent
from database import DB_PATH, init_db

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"

app = FastAPI(
    title="GENOMIND API",
    description="Plataforma de inteligencia genómica para prevenir enfermedades no transmisibles. "
                "Agentes: GENETIX (genética), SIGMA (bioestadística), VITA (estilo de vida), "
                "TERRA (ambiental), NUTRIX (nutrición).",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _snps_for(disease: str) -> list[genetic_agent.Snp]:
    with get_db() as db:
        rows = db.execute("SELECT * FROM snps WHERE disease = ?", (disease,)).fetchall()
    return [genetic_agent.Snp(
        rsid=r["rsid"], gene=r["gene"], disease=r["disease"],
        risk_allele=r["risk_allele"], other_allele=r["other_allele"],
        odds_ratio=r["odds_ratio"], risk_allele_freq=r["risk_allele_freq"],
        note=r["note"] or "") for r in rows]


AGENTS_META = [
    {"id": "genetix", "name": "GENETIX", "role": "Genetista molecular",
     "specialty": "Puntuaciones de riesgo poligénico con 72 variantes GWAS reales de 11 enfermedades",
     "method": "Suma ponderada de log(OR) bajo equilibrio de Hardy-Weinberg; normalización z y percentil poblacional"},
    {"id": "sigma", "name": "SIGMA", "role": "Bioestadístico",
     "specialty": "Motor estadístico completo con salida APA: t-test, chi², OR, ANOVA, correlaciones, potencia",
     "method": "Pruebas paramétricas y no paramétricas con scipy; corrección exacta de Fisher automática"},
    {"id": "vita", "name": "VITA", "role": "Medicina preventiva",
     "specialty": "Interacción gen × ambiente y escenario optimizado evitable",
     "method": "Modelo multiplicativo con multiplicadores citados (DPP, PREDIMED, INTERHEART) e interacciones documentadas"},
    {"id": "terra", "name": "TERRA", "role": "Salud ambiental",
     "specialty": "Atlas de 34 regiones: PM2.5, espacios verdes, caminabilidad y acceso a salud",
     "method": "Guía OMS de Calidad del Aire 2021 aplicada a riesgo por región"},
    {"id": "nutrix", "name": "NUTRIX", "role": "Nutrición de precisión social",
     "specialty": "80 alimentos con IG, sodio, costo y huella hídrica + cesta vital optimizada",
     "method": "Puntuación de salud transparente y greedy de nutrientes por punto de costo"},
]


# ------------------------- Utilidades de validación -------------------------

def _load_json(name: str):
    with open(BASE_DIR / "data" / name, encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------ Modelos Pydantic ---------------------------

class BatchPRSRequest(BaseModel):
    genotypes: dict[str, str] = Field(default_factory=dict)
    diseases: list[str] = Field(default_factory=list)
    simulated: bool = False
    seed: Optional[int] = None
    enriched: bool = False


class GeneEnvironmentRequest(BaseModel):
    genotypes: dict[str, str] = Field(default_factory=dict)
    lifestyle: dict = Field(default_factory=dict)
    region_id: Optional[str] = None
    simulated: bool = False
    seed: Optional[int] = None


class CompareRequest(BaseModel):
    ids: list[int]


class BasketRequest(BaseModel):
    max_cost: Optional[int] = None
    max_items: int = 7


class StatsRequest(BaseModel):
    pass


class TTestRequest(StatsRequest):
    a: list[float]
    b: list[float]
    paired: bool = False


class MannWhitneyRequest(StatsRequest):
    a: list[float]
    b: list[float]


class ChisqRequest(StatsRequest):
    table: list[list[int]]


class ORRequest(StatsRequest):
    a: int
    b: int
    c: int
    d: int


class CorrelationRequest(StatsRequest):
    x: list[float]
    y: list[float]
    method: str = "pearson"


class AnovaRequest(StatsRequest):
    groups: dict[str, list[float]]


class PowerRequest(StatsRequest):
    effect_d: float
    alpha: float = 0.05
    power: float = 0.8
    ratio: float = 1.0


class DatasetRequest(StatsRequest):
    csv_text: str
    group_col: Optional[str] = None
    value_col: Optional[str] = None


class SummaryRequest(StatsRequest):
    values: list[float]


class ProfileRequest(BaseModel):
    name: str
    genotypes: dict[str, str]
    lifestyle: dict
    results: Optional[dict] = None


# -------------------------------- Endpoints --------------------------------

@app.get("/api/health")
def health():
    with get_db() as db:
        n_diseases = db.execute("SELECT COUNT(*) FROM diseases").fetchone()[0]
        n_snps = db.execute("SELECT COUNT(*) FROM snps").fetchone()[0]
        n_foods = db.execute("SELECT COUNT(*) FROM foods").fetchone()[0]
        n_regions = db.execute("SELECT COUNT(*) FROM regions").fetchone()[0]
    return {"status": "ok", "version": "1.0.0", "database": str(DB_PATH),
            "diseases": n_diseases, "snps": n_snps, "foods": n_foods, "regions": n_regions}


@app.get("/api/meta/agents")
def agents_info():
    return AGENTS_META


@app.get("/api/diseases")
def list_diseases():
    with get_db() as db:
        rows = db.execute("SELECT * FROM diseases ORDER BY category, name_es").fetchall()
    out = []
    for r in rows:
        out.append({"code": r["code"], "name": r["name"], "name_es": r["name_es"],
                    "category": r["category"], "baseline_risk": r["baseline_risk"],
                    "baseline_label": r["baseline_label"], "description_es": r["description_es"],
                    "modifiable": json.loads(r["modifiable"])})
    return out


@app.get("/api/diseases/{code}/snps")
def disease_snps(code: str):
    with get_db() as db:
        if db.execute("SELECT 1 FROM diseases WHERE code = ?", (code,)).fetchone() is None:
            raise HTTPException(404, f"Enfermedad {code} no encontrada.")
        rows = db.execute(
            "SELECT rsid, gene, chromosome, risk_allele, other_allele, odds_ratio, "
            "risk_allele_freq, p_value, study, note FROM snps WHERE disease = ?", (code,)
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/snps")
def all_snps(disease: Optional[str] = Query(None)):
    q = "SELECT * FROM snps" + (" WHERE disease = ?" if disease else "")
    with get_db() as db:
        rows = db.execute(q, (disease,) if disease else ()).fetchall()
    return [dict(r) for r in rows]


def _resolve_genotypes(req) -> dict[str, str]:
    """Permite genotipos simulados por defecto para explorar la plataforma."""
    if req.genotypes and not req.simulated:
        return req.genotypes
    diseases = req.diseases if getattr(req, "diseases", None) else None
    with get_db() as db:
        if diseases:
            marks = ",".join("?" * len(diseases))
            rows = db.execute(f"SELECT * FROM snps WHERE disease IN ({marks})",
                              tuple(diseases)).fetchall()
        else:
            rows = db.execute("SELECT * FROM snps").fetchall()
    snps = [genetic_agent.Snp(r["rsid"], r["gene"], r["disease"], r["risk_allele"],
                              r["other_allele"], r["odds_ratio"], r["risk_allele_freq"],
                              r["note"] or "") for r in rows]
    simulator = genetic_agent.simulate_risk_enriched if getattr(req, "enriched", False) \
        else genetic_agent.simulate_genotypes
    sim = simulator(snps, req.seed)
    sim.update({k: v for k, v in req.genotypes.items() if v})
    return sim


@app.post("/api/analysis/polygenic/batch")
def batch_prs(req: BatchPRSRequest):
    if not req.diseases:
        with get_db() as db:
            req.diseases = [r["code"] for r in
                            db.execute("SELECT code FROM diseases").fetchall()]
    genotypes = _resolve_genotypes(req)
    results = []
    for code in req.diseases:
        with get_db() as db:
            if db.execute("SELECT 1 FROM diseases WHERE code = ?", (code,)).fetchone() is None:
                continue
        snps = _snps_for(code)
        prs = genetic_agent.compute_prs(snps, genotypes)
        if prs["rr"] is None:
            continue
        with get_db() as db:
            base = db.execute("SELECT name_es, baseline_risk, baseline_label, category "
                              "FROM diseases WHERE code = ?", (code,)).fetchone()
        abs_risk = min(base["baseline_risk"] * prs["rr"], 0.95)
        results.append({
            "code": code, "name_es": base["name_es"], "category": base["category"],
            "rr": prs["rr"], "percentile": prs["percentile"], "z": prs["z"],
            "abs_risk": round(abs_risk, 4),
            "baseline_risk": base["baseline_risk"], "baseline_label": base["baseline_label"],
            "contributions": prs["contributions"][:8],
            "n_used": prs["n_used"], "n_total": prs["n_total"],
            "disclaimer": genetic_agent.DISCLAIMER,
        })
    return {"results": results, "genotypes_used": genotypes,
            "disclaimer": genetic_agent.DISCLAIMER}


def _get_region(region_id: Optional[str]):
    if not region_id:
        return None
    with get_db() as db:
        row = db.execute("SELECT * FROM regions WHERE id = ?", (region_id,)).fetchone()
    return dict(row) if row else None


@app.post("/api/analysis/gene-environment")
def gene_environment(req: GeneEnvironmentRequest):
    with get_db() as db:
        codes = [r["code"] for r in db.execute("SELECT code FROM diseases").fetchall()]
        rows = db.execute("SELECT * FROM snps").fetchall()
    snps_by_disease: dict[str, list[genetic_agent.Snp]] = {c: [] for c in codes}
    for r in rows:
        snps_by_disease.setdefault(r["disease"], []).append(genetic_agent.Snp(
            r["rsid"], r["gene"], r["disease"], r["risk_allele"], r["other_allele"],
            r["odds_ratio"], r["risk_allele_freq"], r["note"] or ""))
    genotypes = _resolve_genotypes(req)
    region = _get_region(req.region_id)
    analysis = lifestyle_agent.gene_environment_analysis(
        snps_by_disease, genotypes, req.lifestyle, region)
    analysis["genotypes_used"] = genotypes
    return analysis


@app.get("/api/regions")
def list_regions(country: Optional[str] = Query(None)):
    q = "SELECT * FROM regions"
    params = ()
    if country:
        q += " WHERE country LIKE ?"
        params = (f"%{country}%",)
    with get_db() as db:
        rows = db.execute(q, params).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/foods")
def search_foods(q: Optional[str] = Query(None), category: Optional[str] = Query(None),
                max_cost: Optional[int] = Query(None)):
    query = "SELECT * FROM foods WHERE 1=1"
    params: list = []
    if q:
        query += " AND (name LIKE ? OR region LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    if category:
        query += " AND category = ?"
        params.append(category)
    if max_cost:
        query += " AND cost_index <= ?"
        params.append(max_cost)
    query += " ORDER BY name"
    with get_db() as db:
        rows = db.execute(query, params).fetchall()
    foods = [dict(r) for r in rows]
    for f in foods:
        f["health_score"] = nutrition_agent.health_score(f)
    return foods


@app.post("/api/foods/compare")
def compare_foods(req: CompareRequest):
    if not req.ids:
        raise HTTPException(400, "Indique al menos un id de alimento.")
    if len(req.ids) > 4:
        req.ids = req.ids[:4]
    marks = ",".join("?" * len(req.ids))
    with get_db() as db:
        rows = db.execute(f"SELECT * FROM foods WHERE id IN ({marks})",
                         tuple(req.ids)).fetchall()
    foods = [dict(r) for r in rows]
    if not foods:
        raise HTTPException(404, "Alimentos no encontrados.")
    return nutrition_agent.compare_foods(foods)


@app.post("/api/nutrition/basket")
def basket(req: BasketRequest):
    with get_db() as db:
        rows = db.execute("SELECT * FROM foods").fetchall()
    foods = [dict(r) for r in rows]
    return nutrition_agent.vital_basket(foods, req.max_cost, req.max_items)


# ----------------------------- Endpoints SIGMA -----------------------------

@app.post("/api/stats/summary")
def stats_summary(req: SummaryRequest):
    return statistical_agent.summary(req.values)


@app.post("/api/stats/ttest")
def stats_ttest(req: TTestRequest):
    return statistical_agent.ttest(req.a, req.b, req.paired)


@app.post("/api/stats/mannwhitney")
def stats_mannwhitney(req: MannWhitneyRequest):
    return statistical_agent.mannwhitney(req.a, req.b)


@app.post("/api/stats/chisq")
def stats_chisq(req: ChisqRequest):
    return statistical_agent.chisq(req.table)


@app.post("/api/stats/or")
def stats_or(req: ORRequest):
    return statistical_agent.odds_ratio(req.a, req.b, req.c, req.d)


@app.post("/api/stats/correlation")
def stats_correlation(req: CorrelationRequest):
    return statistical_agent.correlation(req.x, req.y, req.method)


@app.post("/api/stats/anova")
def stats_anova(req: AnovaRequest):
    return statistical_agent.anova(req.groups)


@app.post("/api/stats/power")
def stats_power(req: PowerRequest):
    return statistical_agent.power_two_means(req.effect_d, req.alpha, req.power, req.ratio)


@app.post("/api/stats/dataset")
def stats_dataset(req: DatasetRequest):
    return statistical_agent.analyze_dataset(req.csv_text, req.group_col, req.value_col)


# ------------------------------ Perfiles (SQLite) --------------------------

@app.get("/api/profiles")
def list_profiles():
    with get_db() as db:
        rows = db.execute("SELECT id, name, created_at FROM profiles ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


@app.post("/api/profiles")
def save_profile(req: ProfileRequest):
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO profiles (name, genotypes, lifestyle, results) VALUES (?,?,?,?)",
            (req.name, json.dumps(req.genotypes), json.dumps(req.lifestyle),
             json.dumps(req.results) if req.results else None))
        db.commit()
        pid = cur.lastrowid
    return {"id": pid, "name": req.name, "saved": True}


@app.get("/api/profiles/{pid}")
def get_profile(pid: int):
    with get_db() as db:
        row = db.execute("SELECT * FROM profiles WHERE id = ?", (pid,)).fetchone()
    if row is None:
        raise HTTPException(404, "Perfil no encontrado.")
    out = dict(row)
    out["genotypes"] = json.loads(out["genotypes"])
    out["lifestyle"] = json.loads(out["lifestyle"])
    if out.get("results"):
        out["results"] = json.loads(out["results"])
    return out


@app.delete("/api/profiles/{pid}")
def delete_profile(pid: int):
    with get_db() as db:
        cur = db.execute("DELETE FROM profiles WHERE id = ?", (pid,))
        db.commit()
    return {"deleted": cur.rowcount > 0}


# ------------------------------ Frontend estático -------------------------

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
