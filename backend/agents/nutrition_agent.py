"""Agent NUTRIX — nutricionista de precisión con perspectiva social.

Comparador de alimentos, puntuación de salud transparente y la
'cesta vital' optimizada: la combinación más barata que cubre
proteína y fibra diarias. Pensado para que la mejor alimentación
no sea un privilegio económico.
"""
from typing import Optional

PROTEIN_TARGET_G = 50.0
FIBER_TARGET_G = 25.0


def health_score(food: dict) -> int:
    """0-100. Fórmula transparente y documentada:
    base densidad nutricional + fibra/bonus - penalizaciones (azúcar, IG, sodio)."""
    kcal = max(food["kcal"], 1)
    score = 50.0
    score += min(food["fiber_g"] * 2.2, 22)
    score += min(food["protein_g"] / kcal * 1000 * 0.15, 12)
    if food["potassium_mg"]:
        score += min(food["potassium_mg"] / 60, 8)
    if food["kcal"] < 100:
        score += 6
    gi = food["glycemic_index"]
    if gi:
        if gi >= 70:
            score -= 14
        elif gi >= 55:
            score -= 7
        elif gi <= 20:
            score += 8
    score -= min(food["sugar_g"] * 0.45, 18)
    score -= min(food["sodium_mg"] / 45, 14)
    if food["kcal"] > 500 and food["fiber_g"] < 3:
        score -= 6
    return max(0, min(100, round(score)))


def classify(value: float, good_max: float, warn_max: float) -> str:
    if value <= good_max:
        return "bajo"
    if value <= warn_max:
        return "medio"
    return "alto"


def compare_foods(foods: list[dict]) -> dict:
    if not foods:
        return {"error": "Sin alimentos."}
    keys = ["kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "glycemic_index",
            "sodium_mg", "potassium_mg", "sugar_g", "cost_index", "water_l"]
    best = {}
    for k in keys:
        vals = [f[k] for f in foods if f[k] is not None]
        if not vals:
            continue
        lower_better = k in ("kcal", "glycemic_index", "sodium_mg", "sugar_g",
                             "cost_index", "water_l", "carbs_g", "fat_g")
        best[k] = min(vals) if lower_better else max(vals)
    for f in foods:
        f["health_score"] = health_score(f)
        f["glycemic_class"] = classify(f["glycemic_index"] or 0, 55, 70) if f["glycemic_index"] else "n/a"
        f["density"] = round(f["protein_g"] * 4 / max(f["kcal"], 1) * 100, 1)
    ranked = sorted(foods, key=lambda x: x["health_score"], reverse=True)
    cheapest = min(foods, key=lambda x: x["cost_index"])
    greenest = min(foods, key=lambda x: x["water_l"])
    return {
        "foods": foods,
        "best_per_nutrient": best,
        "ranking": [{"name": f["name"], "health_score": f["health_score"]} for f in ranked],
        "winner": ranked[0]["name"],
        "cheapest": cheapest["name"],
        "lowest_water": greenest["name"],
        "insight": (
            f"{ranked[0]['name']} encabeza la puntuación de salud ({ranked[0]['health_score']}/100). "
            f"La opción más económica es {cheapest['name']} y la de menor huella hídrica, "
            f"{greenest['name']}."
        ),
    }


def vital_basket(foods: list[dict], max_cost: Optional[int] = None,
                 max_items: int = 7) -> dict:
    """Cesta vital: greedy de proteína y fibra por punto de costo.

    Prioriza nutrientes por unidad de costo, prioriza la diversidad
    de categorías y cierra con la proteína de menor costo del pool.
    """
    pool = [f for f in foods if max_cost is None or f["cost_index"] <= max_cost]
    if not pool:
        pool = foods
    scored = []
    for f in pool:
        density = (f["protein_g"] / PROTEIN_TARGET_G + f["fiber_g"] / FIBER_TARGET_G)
        per_cost = density / max(f["cost_index"], 1)
        scored.append((per_cost, density, f))
    scored.sort(key=lambda x: x[0], reverse=True)

    selected: list[dict] = []
    categories = set()
    protein = fiber = kcal = 0.0
    water = 0
    cost_points = 0
    for per_cost, density, f in scored:
        if len(selected) >= max_items:
            break
        remaining_p = PROTEIN_TARGET_G - protein
        remaining_f = FIBER_TARGET_G - fiber
        if remaining_p <= 2 and remaining_f <= 2:
            break
        contribution = f["protein_g"] / PROTEIN_TARGET_G + f["fiber_g"] / FIBER_TARGET_G
        need = max(remaining_p / PROTEIN_TARGET_G, remaining_f / FIBER_TARGET_G, 0)
        if contribution < need * 0.08 and len(selected) >= 3:
            continue
        selected.append(f)
        categories.add(f["category"])
        factor = 1.0
        if remaining_p > 0 and (f["protein_g"] / PROTEIN_TARGET_G) > need:
            factor = need / max(f["protein_g"] / PROTEIN_TARGET_G, 1e-9)
        factor = min(max(factor, 0.3), 1.0)
        protein += f["protein_g"] * factor
        fiber += f["fiber_g"] * factor
        kcal += f["kcal"] * factor
        water += f["water_l"] * factor
        cost_points += f["cost_index"] * factor

    if protein < PROTEIN_TARGET_G * 0.85:
        protein_foods = [f for f in pool if f["protein_g"] >= 15]
        if protein_foods:
            cheapest_protein = min(protein_foods, key=lambda x: x["cost_index"] / max(x["protein_g"], 1))
            if cheapest_protein["name"] not in [s["name"] for s in selected]:
                factor = min((PROTEIN_TARGET_G - protein) / max(cheapest_protein["protein_g"], 1), 1.5)
                selected.append(cheapest_protein)
                categories.add(cheapest_protein["category"])
                protein += cheapest_protein["protein_g"] * factor
                fiber += cheapest_protein["fiber_g"] * factor
                kcal += cheapest_protein["kcal"] * factor
                water += cheapest_protein["water_l"] * factor
                cost_points += cheapest_protein["cost_index"] * factor

    total_points = sum(f["cost_index"] for f in selected)
    return {
        "items": [{"name": f["name"], "category": f["category"], "cost_index": f["cost_index"],
                   "note": f["note"]} for f in selected],
        "estimated_daily": {
            "protein_g": round(protein, 1), "fiber_g": round(fiber, 1),
            "kcal": round(kcal), "water_l": round(water),
            "cost_points": round(cost_points, 1)},
        "coverage": {
            "protein_pct": round(protein / PROTEIN_TARGET_G * 100),
            "fiber_pct": round(fiber / FIBER_TARGET_G * 100)},
        "total_cost_index": total_points,
        "categories": sorted(categories),
        "message": (
            "Cesta optimizada: maximiza proteína (50 g) y fibra (25 g) diarias por punto de costo. "
            "El frijol, la lenteja, el huevo, la sardina y el maní son los campeones silenciosos "
            "de la nutrición de bajo presupuesto en todo el mundo."
        ),
    }
