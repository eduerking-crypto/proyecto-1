"""Agentes VITA (estilo de vida) y TERRA (ambiental).

Motor gen × ambiente: combina la puntuación poligénica del agente
GENETIX con multiplicadores ambientales basados en evidencia y
documenta las interacciones gen-ambiente publicadas. Genera el
escenario optimizado (todos los factores modificables a su mejor
valor) para cuantificar cuánto riesgo es realmente evitable.
"""
import json
import math
from pathlib import Path
from typing import Optional

from agents.genetic_agent import Snp, compute_prs

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

with open(DATA_DIR / "lifestyle.json", encoding="utf-8") as _fh:
    LIFESTYLE = json.load(_fh)

with open(DATA_DIR / "diseases.json", encoding="utf-8") as _fh:
    DISEASES = {d["code"]: d for d in json.load(_fh)}


def bmi_category(bmi: float) -> Optional[dict]:
    for cat in LIFESTYLE["bmi_categories"]["categories"]:
        if cat["range"][0] <= bmi < cat["range"][1]:
            return cat
    return None


def pm25_category(pm25: float) -> Optional[dict]:
    for cat in LIFESTYLE["pm25_categories"]["categories"]:
        if cat["range"][0] <= pm25 < cat["range"][1]:
            return cat
    return None


def _factor_block(lifestyle: dict, factor: str) -> tuple[str, dict]:
    value = lifestyle.get(factor) or ""
    options = LIFESTYLE["factors"][factor]["options"]
    key = value if value in options else next(iter(options))
    return key, options[key]


def lifestyle_scores(lifestyle: dict) -> dict:
    """Puntuación 0-100 por eje para el radar del frontend."""
    table = LIFESTYLE["lifestyle_scores"]
    out = {}
    out["tabaquismo"] = table["tabaquismo"].get(lifestyle.get("smoking"), 55)
    out["actividad"] = table["actividad"].get(lifestyle.get("activity"), 45)
    out["dieta"] = table["dieta"].get(lifestyle.get("diet"), 55)
    out["alcohol"] = table["alcohol"].get(lifestyle.get("alcohol"), 70)
    out["sueño"] = table["sueño"].get(lifestyle.get("sleep"), 60)
    out["estrés"] = table["estres"].get(lifestyle.get("stress"), 50)
    fv = int(lifestyle.get("servings_fv") or 0)
    out["frutas/verduras"] = min(fv / 5, 1.2) * 80
    out["frutas/verduras"] = round(min(out["frutas/verduras"], 100))
    return out


def _multipliers(lifestyle: dict, region_pm25: Optional[float]) -> tuple[dict, list]:
    """Multiplicadores por enfermedad + registro legible de factores aplicados."""
    applied: list[dict] = []

    def apply(factor_label: str, value_key: str, mults: dict, option_label: str):
        for disease, m in mults.items():
            mults_all.setdefault(disease, 1.0)
            mults_all[disease] *= m
        if mults:
            applied.append({"factor": factor_label, "option": option_label,
                            "diseases": mults})

    mults_all: dict[str, float] = {}
    for factor in ("smoking", "activity", "diet", "alcohol", "sleep", "stress"):
        key, option = _factor_block(lifestyle, factor)
        label = LIFESTYLE["factors"][factor]["label"]
        apply(label, key, option["multipliers"], option["label"])

    weight = lifestyle.get("weight_kg")
    height = lifestyle.get("height_cm")
    bmi = None
    if weight and height and float(height) > 50:
        bmi = float(weight) / (float(height) / 100) ** 2
        cat = bmi_category(bmi)
        if cat:
            apply("IMC", cat["key"], cat["multipliers"], f"{cat['label']} (IMC {bmi:.1f})")

    if region_pm25 is not None:
        cat = pm25_category(float(region_pm25))
        if cat:
            apply("Aire (PM2.5)", cat["key"], cat["multipliers"],
                  f"{cat['label']} — {region_pm25} µg/m³")

    fv = int(lifestyle.get("servings_fv") or 0)
    fv_cfg = LIFESTYLE["fruit_veg_adjustment"]
    if fv < fv_cfg["low_threshold"]:
        apply("Frutas y verduras", "bajo", fv_cfg["low_penalty"],
              f"{fv} porciones/día (< {fv_cfg['low_threshold']})")
    elif fv >= fv_cfg["optimal"]:
        apply("Frutas y verduras", "optimo", fv_cfg["optimal_bonus"],
              f"{fv} porciones/día (≥ {fv_cfg['optimal']})")

    return mults_all, applied


OPTIMIZED = {
    "smoking": "nunca", "activity": "intenso", "diet": "mediterranea",
    "alcohol": "ninguno", "sleep": "adecuado", "stress": "bajo",
    "servings_fv": 5,
}


def _interaction_adjustments(disease: str, lifestyle: dict, genotypes: dict,
                             snps: list[Snp], prs_result: dict) -> dict:
    """Interacciones gen-ambiente documentadas en la literatura."""
    active = []
    if disease in ("OBES", "T2D"):
        if lifestyle.get("activity") in ("moderado", "intenso") and \
                any(s.rsid == "rs9939609" for s in snps):
            dosage = None
            for c in prs_result["contributions"]:
                if c["rsid"] == "rs9939609":
                    dosage = c["dosage"]
                    break
            if dosage:
                active.append({
                    "id": "fto_pa",
                    "detail": "Realiza actividad física regular siendo portador del alelo FTO: "
                              "el efecto genético sobre el IMC está atenuado ~30%.",
                    "source": "Kilpeläinen et al., PLoS Medicine 2011"})
    if disease == "ALZ" and lifestyle.get("activity") in ("moderado", "intenso"):
        if any(c["rsid"] == "rs429358" and c["dosage"] > 0
               for c in prs_result["contributions"]):
            active.append({
                "id": "apoe_pa",
                "detail": "Portador de APOE ε4 físicamente activo: el ejercicio atenúa "
                          "sustancialmente el riesgo de deterioro cognitivo.",
                "source": "Rovio et al. 2005; meta-análisis de portadores ε4 activos"})
    if disease == "LUNG" and lifestyle.get("smoking") == "nunca":
        active.append({
            "id": "chrna5_smoke",
            "detail": "Nunca fumador: las variantes de CHRNA5 (dependencia nicotínica) "
                      "apenas afectan su riesgo. El 80-90% del cáncer de pulmón es "
                      "atribuible al humo de tabaco.",
            "source": "Le Marchand et al. 2008; IARC"})
    if disease == "T2D":
        active.append({
            "id": "tcf7l2_dpp",
            "detail": "Sea cual sea su genotipo TCF7L2, el ensayo Diabetes Prevention "
                      "Program demostró que la intervención intensiva en estilo de vida "
                      "reduce la progresión a diabetes un 58%.",
            "source": "Knowler et al., NEJM 2002"})
    if disease == "CAD" and lifestyle.get("smoking") == "fumador":
        if any(c["rsid"] == "rs1333049" and c["dosage"] > 0
               for c in prs_result["contributions"]):
            active.append({
                "id": "p21_smoke",
                "detail": "Portador del alelo 9p21 (rs1333049) que además fuma: el riesgo "
                          "combinado excede la suma de ambos factores por separado. Dejar "
                          "de fumar es su palanca más potente.",
                "source": "CARDIoGRAMplusC4D; McPherson & Davies 2012"})
    return active


def recommendations_for(disease: str, lifestyle: dict, mults_used: list[dict]) -> list[dict]:
    """Recomendaciones priorizadas y citadas generadas para una enfermedad."""
    recs = []
    used_factors = {m["factor"] for m in mults_used}
    if disease in ("T2D", "CAD", "HTN", "OBES", "CRC", "BREAST", "ALZ", "CKD", "LUNG"):
        if "Tabaquismo" in used_factors and lifestyle.get("smoking") != "nunca":
            recs.append({
                "priority": "alta",
                "title": "Plan de cesación tabáquica",
                "detail": "Dejar de fumar reduce a la mitad el exceso de riesgo cardiovascular en 1 año "
                          "y es la intervención con mayor impacto sobre el cáncer de pulmón. "
                          "Farmacoterapia (vareniclina/NRT) duplica la tasa de éxito.",
                "evidence": "US Surgeon General 2010; IARC"})
        if lifestyle.get("activity") in ("sedentario", "ligero"):
            recs.append({
                "priority": "alta",
                "title": "150 minutos de movimiento por semana",
                "detail": "Caminar a paso vivo 30 min, 5 días/semana reduce el riesgo de diabetes ~35%, "
                          "cardiopatía ~30% y deterioro cognitivo ~35%. Es la relación beneficio/costo "
                          "más alta de toda la medicina preventiva.",
                "evidence": "Diabetes Prevention Program (NEJM 2002); Moore et al., Lancet 2012"})
        if lifestyle.get("diet") in ("occidental", "mixta"):
            recs.append({
                "priority": "alta",
                "title": "Transición hacia patrón mediterráneo local",
                "detail": "PREDIMED demostró -30% de eventos cardiovasculares con aceite de oliva, "
                          "frutos secos, legumbres y pescado. La versión andina/tropical existe: "
                          "maíz nixtamalizado, frijoles, aguacate, guayaba y sardinas.",
                "evidence": "Estruch et al., NEJM 2013/2018 (PREDIMED)"})
        if "IMC" in used_factors:
            recs.append({
                "priority": "media",
                "title": "Objetivo de peso realista: -5-10%",
                "detail": "Perder solo 5-10% del peso corporal mejora sensiblemente la glucemia, "
                          "presión arterial y perfil lipídico. El DPP logró 58% menos diabetes con "
                          "ese objetivo en personas con prediabetes.",
                "evidence": "Diabetes Prevention Program; Look AHEAD (NEJM 2013)"})
        if lifestyle.get("sleep") == "corto":
            recs.append({
                "priority": "media",
                "title": "Higiene del sueño: objetivo 7-8 h",
                "detail": "Dormir <6 h eleva glucemia, presión arterial y cortisol. El sueño profundo "
                          "es cuando el cerebro elimina el amiloide β.",
                "evidence": "Cappuccio et al. (meta-análisis); Xie et al., Science 2013"})
        if lifestyle.get("stress") == "alto":
            recs.append({
                "priority": "media",
                "title": "Intervención sobre estrés crónico",
                "detail": "El estrés psicosocial multiplicó por 2.5 el riesgo de infarto en INTERHEART. "
                          "Respiración diafragmática (10 min/día) y contacto con espacios verdes "
                          "reducen cortisol y presión arterial.",
                "evidence": "INTERHEART (Lancet 2004); estudios de espacios verdes urbanos"})
        if "Alcohol" in used_factors and lifestyle.get("alcohol") == "alto":
            recs.append({
                "priority": "media",
                "title": "Reducir alcohol a cero o mínimo",
                "detail": "El alcohol eleva presión arterial y el riesgo de al menos 7 cánceres. "
                          "La OMS concluye que no existe un nivel seguro.",
                "evidence": "GBD Alcohol Collaborators, Lancet 2018"})
    if disease == "LUNG" and lifestyle.get("smoking") == "fumador":
        recs.insert(0, {
            "priority": "critica",
            "title": "Cribado de pulmón + cesación inmediata",
            "detail": "Con historia de tabaquismo intensa, la tomografía de baja dosis reduce la "
                      "mortalidad por cáncer de pulmón un 20% (NLST). Combinada con cesación, es "
                      "la estrategia con mayor impacto absoluto de toda la plataforma.",
            "evidence": "National Lung Screening Trial (NEJM 2011)"})
    return recs[:4]


def gene_environment_analysis(snps_by_disease: dict[str, list[Snp]],
                              genotypes: dict, lifestyle: dict,
                              region: Optional[dict]) -> dict:
    """Análisis completo gen × ambiente para las enfermedades del panel."""
    region_pm25 = float(region["pm25"]) if region else None
    mults_all, mults_used = _multipliers(lifestyle, region_pm25)

    weight = lifestyle.get("weight_kg")
    height = lifestyle.get("height_cm")
    bmi = None
    if weight and height and float(height) > 50:
        bmi = float(weight) / (float(height) / 100) ** 2

    opt_lifestyle = dict(lifestyle)
    opt_lifestyle.update(OPTIMIZED)
    opt_mults, _ = _multipliers(opt_lifestyle, min(region_pm25, 15) if region_pm25 else None)

    diseases_out = []
    for code, snps in snps_by_disease.items():
        disease = DISEASES.get(code)
        if not disease:
            continue
        prs = compute_prs(snps, genotypes)
        if prs["rr"] is None:
            continue
        interactions = _interaction_adjustments(code, lifestyle, genotypes, snps, prs)
        rr_gen = prs["rr"]
        mult = mults_all.get(code, 1.0)
        if any(i["id"] == "fto_pa" for i in interactions):
            mult *= 0.85
        if any(i["id"] == "apoe_pa" for i in interactions):
            mult *= 0.7
        if code == "LUNG" and lifestyle.get("smoking") == "nunca":
            rr_gen_display = max(rr_gen ** 0.5, 0.9)
        else:
            rr_gen_display = rr_gen
        rr_combined = min(rr_gen_display * mult, 25.0)
        baseline = disease["baseline_risk"]
        abs_gen = min(baseline * rr_gen_display, 0.95)
        abs_comb = min(baseline * rr_combined, 0.95)
        rr_opt = min(rr_gen_display * opt_mults.get(code, 1.0), 25.0)
        abs_opt = min(baseline * rr_opt, 0.95)
        reducible = max(abs_comb - abs_opt, 0.0)
        reducible_fraction = (reducible / abs_comb * 100) if abs_comb > 0 else 0.0
        diseases_out.append({
            "code": code,
            "name_es": disease["name_es"],
            "category": disease["category"],
            "percentile": prs["percentile"],
            "rr_genetic": round(rr_gen_display, 2),
            "rr_combined": round(rr_combined, 2),
            "abs_genetic": round(abs_gen, 4),
            "abs_combined": round(abs_comb, 4),
            "abs_optimized": round(abs_opt, 4),
            "reducible_points": round(reducible, 4),
            "reducible_fraction_pct": round(reducible_fraction, 1),
            "top_snps": prs["contributions"][:5],
            "multipliers_used": [m for m in mults_used if code in m.get("diseases", {})],
            "interactions": interactions,
            "recommendations": recommendations_for(code, lifestyle,
                                                    [m for m in mults_used if code in m.get("diseases", {})]),
        })

    bmi_out = None
    if bmi:
        cat = bmi_category(bmi)
        bmi_out = {"value": round(bmi, 1), "category": cat["key"] if cat else "fuera_de_rango",
                   "label": cat["label"] if cat else "IMC fuera de rango"}

    return {
        "bmi": bmi_out,
        "lifestyle_scores": lifestyle_scores(lifestyle),
        "region": region,
        "diseases": diseases_out,
        "disclaimer": ("Modelo multiplicativo simplificado con fines educativos: los OR "
                       "genéticos y los multiplicadores ambientales provienen de estudios "
                       "poblacionales distintos y su combinación exacta requiere modelos "
                       "formales de interacción. No sustituye evaluación clínica individual."),
    }
