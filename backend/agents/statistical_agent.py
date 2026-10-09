"""Agent SIGMA — bioestadístico.

Motor estadístico con salida en formato APA: t-test (Welch y pareado),
Mann-Whitney, chi-cuadrado con corrección de Fisher, odds ratio de
tablas 2x2, correlaciones, ANOVA de una vía, análisis de potencia y
exploración automática de conjuntos de datos CSV.
"""
import csv
import io
import math
from typing import Optional

import numpy as np
from scipy import stats


def _clean(values) -> np.ndarray:
    arr = np.asarray([v for v in values if v is not None], dtype=float)
    return arr[np.isfinite(arr)]


def apa_p(p: float) -> str:
    if p < 0.001:
        return "p < .001"
    if p >= 0.999:
        return "p = .999"
    return f"p = {p:.3f}".replace("0.", ".", 1)


def summary(values) -> dict:
    a = _clean(values)
    n = int(a.size)
    if n == 0:
        return {"error": "Sin datos numéricos válidos."}
    mean = float(np.mean(a))
    sd = float(np.std(a, ddof=1)) if n > 1 else 0.0
    sem = sd / math.sqrt(n) if n > 1 else 0.0
    ci = None
    if n > 1:
        t = stats.t.ppf(0.975, n - 1)
        ci = [mean - t * sem, mean + t * sem]
    q1, med, q3 = (float(x) for x in np.percentile(a, [25, 50, 75]))
    return {
        "n": n, "mean": round(mean, 4), "sd": round(sd, 4), "median": round(med, 4),
        "sem": round(sem, 4), "ci95_mean": [round(x, 4) for x in ci] if ci else None,
        "q1": round(q1, 4), "q3": round(q3, 4), "iqr": round(q3 - q1, 4),
        "min": float(np.min(a)), "max": float(np.max(a)),
        "skew": round(float(stats.skew(a)), 3) if n >= 3 else None,
        "kurtosis": round(float(stats.kurtosis(a)), 3) if n >= 4 else None,
        "cv_pct": round(sd / abs(mean) * 100, 2) if mean != 0 else None,
    }


def ttest(a, b, paired: bool = False) -> dict:
    x, y = _clean(a), _clean(b)
    if x.size < 2 or y.size < 2:
        return {"error": "Cada grupo necesita al menos 2 valores numéricos."}
    if paired:
        n = min(x.size, y.size)
        x2, y2 = x[:n], y[:n]
        res = stats.ttest_rel(x2, y2)
        diff = x2 - y2
        sd_diff = float(np.std(diff, ddof=1))
        dof = n - 1
        d = abs(float(np.mean(diff)) / sd_diff) if sd_diff > 0 else 0.0
        apa = f"t({dof}) = {res.statistic:.2f}, {apa_p(float(res.pvalue))}, d = {d:.2f}"
        return {"statistic": round(float(res.statistic), 4), "p": float(res.pvalue),
                "dof": dof, "mean_diff": round(float(np.mean(diff)), 4),
                "cohen_d": round(d, 3), "apa": apa, "test": "t pareado"}
    res = stats.ttest_ind(x, y, equal_var=False)
    nx, ny = x.size, y.size
    sx2 = float(np.var(x, ddof=1))
    sy2 = float(np.var(y, ddof=1))
    se = math.sqrt(sx2 / nx + sy2 / ny)
    pooled_sd = math.sqrt(((nx - 1) * sx2 + (ny - 1) * sy2) / (nx + ny - 2))
    dof = (sx2 / nx + sy2 / ny) ** 2 / ((sx2 / nx) ** 2 / (nx - 1) + (sy2 / ny) ** 2 / (ny - 1))
    d = abs(float(np.mean(x) - np.mean(y)) / pooled_sd) if pooled_sd > 0 else 0.0
    t_crit = stats.t.ppf(0.975, dof)
    mdiff = float(np.mean(x) - np.mean(y))
    apa = f"t({dof:.0f}) = {res.statistic:.2f}, {apa_p(float(res.pvalue))}, d = {d:.2f}"
    return {"statistic": round(float(res.statistic), 4), "p": float(res.pvalue),
            "dof": round(dof, 1), "mean_diff": round(mdiff, 4),
            "ci95_diff": [round(mdiff - t_crit * se, 4), round(mdiff + t_crit * se, 4)],
            "cohen_d": round(d, 3), "apa": apa, "test": "t de Welch"}


def mannwhitney(a, b) -> dict:
    x, y = _clean(a), _clean(b)
    if x.size < 2 or y.size < 2:
        return {"error": "Cada grupo necesita al menos 2 valores."}
    res = stats.mannwhitneyu(x, y, alternative="two-sided")
    apa = f"U = {float(res.statistic):.0f}, {apa_p(float(res.pvalue))}"
    return {"statistic": float(res.statistic), "p": float(res.pvalue),
            "median_x": round(float(np.median(x)), 4), "median_y": round(float(np.median(y)), 4),
            "apa": apa, "test": "U de Mann-Whitney"}


def chisq(table: list[list]) -> dict:
    t = np.asarray(table, dtype=float)
    if t.ndim != 2 or min(t.shape) < 2 or np.nansum(t) <= 0:
        return {"error": "Tabla 2x2 o mayor con frecuencias positivas."}
    expected = np.outer(t.sum(axis=1), t.sum(axis=0)) / t.sum()
    low_expected = bool(np.any(expected < 5))
    chi2, p, dof, exp = stats.chi2_contingency(t, correction=(t.shape == (2, 2)))
    n = float(t.sum())
    cramers_v = math.sqrt(chi2 / (n * (min(t.shape) - 1))) if n > 0 else 0.0
    apa = f"χ²({dof}, N = {int(n)}) = {chi2:.2f}, {apa_p(float(p))}, V = {cramers_v:.3f}"
    out = {"statistic": round(float(chi2), 4), "p": float(p), "dof": int(dof),
           "expected": [[round(float(v), 2) for v in row] for row in exp],
           "cramers_v": round(float(cramers_v), 4), "apa": apa,
           "warning_low_expected": low_expected, "test": "Chi-cuadrado de Pearson"}
    if low_expected:
        oddsr, pf = stats.fisher_exact(t) if t.shape == (2, 2) else (None, None)
        if pf is not None:
            out["fisher_exact_p"] = float(pf)
            out["apa_fisher"] = f"Prueba exacta de Fisher: {apa_p(float(pf))}"
    return out


def odds_ratio(a: int, b: int, c: int, d: int) -> dict:
    """Tabla 2x2: [expuesto+caso=a, expuesto+control=b, no expuesto+caso=c, no expuesto+control=d]."""
    cells = [a, b, c, d]
    if any(v < 0 for v in cells) or (a * d + b * c) == 0:
        return {"error": "Celdas no negativas y al menos un caso en cada diagonal."}
    if a + b == 0 or c + d == 0 or a + c == 0 or b + d == 0:
        return {"error": "Filas o columnas nulas: OR indefinido."}
    zero_adj = 0.5 if min(cells) == 0 else 0.0
    aa, bb, cc, dd = (v + zero_adj for v in (a, b, c, d))
    orv = (aa * dd) / (bb * cc)
    se = math.sqrt(1 / aa + 1 / bb + 1 / cc + 1 / dd)
    lo, hi = math.exp(math.log(orv) - 1.96 * se), math.exp(math.log(orv) + 1.96 * se)
    if zero_adj == 0:
        _, pf = stats.fisher_exact([[a, b], [c, d]])
    else:
        pf = None
    apa_or = f"{orv:.2f} (IC95% [{lo:.2f}, {hi:.2f}])"
    out = {"odds_ratio": round(float(orv), 4), "log_or": round(math.log(orv), 4),
           "se": round(se, 4), "ci95": [round(lo, 3), round(hi, 3)],
           "ci95_string": apa_or,
           "fisher_p": float(pf) if pf is not None else None,
           "apa": f"OR = {apa_or}" + (f", {apa_p(float(pf))}" if pf is not None else ""),
           "haldane_adjusted": bool(zero_adj)}
    return out


def correlation(x, y, method: str = "pearson") -> dict:
    xv, yv = _clean(x), _clean(y)
    n = min(xv.size, yv.size)
    if n < 3:
        return {"error": "Se requieren al menos 3 pares."}
    xv, yv = xv[:n], yv[:n]
    if method == "spearman":
        r, p = stats.spearmanr(xv, yv)
        name = "rho de Spearman"
    else:
        r, p = stats.pearsonr(xv, yv)
        name = "r de Pearson"
    if not math.isfinite(r):
        return {"error": "Varianza cero: correlación indefinida."}
    r_clamped = max(min(float(r), 0.999999), -0.999999)
    z = 0.5 * math.log((1 + r_clamped) / (1 - r_clamped))
    se = 1 / math.sqrt(n - 3)
    lo, hi = math.tanh(z - 1.96 * se), math.tanh(z + 1.96 * se)
    return {"r": round(float(r), 4), "p": float(p), "r_squared": round(float(r) ** 2, 4),
            "n": int(n), "ci95": [round(lo, 3), round(hi, 3)],
            "apa": f"{name} = {r:.3f}, {apa_p(float(p))}"}


def anova(groups: dict[str, list]) -> dict:
    arrays = {k: _clean(v) for k, v in groups.items() if len(_clean(v)) >= 2}
    if len(arrays) < 2:
        return {"error": "Se requieren al menos 2 grupos con 2+ valores."}
    res = stats.f_oneway(*arrays.values())
    all_vals = np.concatenate(list(arrays.values()))
    grand = float(np.mean(all_vals))
    ss_between = sum(a.size * (float(np.mean(a)) - grand) ** 2 for a in arrays.values())
    ss_within = sum(float(np.sum((a - np.mean(a)) ** 2)) for a in arrays.values())
    ss_total = ss_between + ss_within
    eta2 = ss_between / ss_total if ss_total > 0 else 0.0
    dof_b = len(arrays) - 1
    dof_w = int(all_vals.size - len(arrays))
    apa = f"F({dof_b}, {dof_w}) = {float(res.statistic):.2f}, {apa_p(float(res.pvalue))}, η² = {eta2:.3f}"
    return {"statistic": round(float(res.statistic), 4), "p": float(res.pvalue),
            "dof": [dof_b, dof_w], "eta_squared": round(float(eta2), 4), "apa": apa,
            "group_means": {k: round(float(np.mean(a)), 4) for k, a in arrays.items()},
            "group_ns": {k: int(a.size) for k, a in arrays.items()},
            "test": "ANOVA de una vía"}


def power_two_means(effect_d: float, alpha: float = 0.05, power: float = 0.8,
                    ratio: float = 1.0) -> dict:
    """Tamaño muestral por grupo para comparar dos medias (aproximación normal)."""
    if effect_d <= 0 or not (0 < alpha < 0.5) or not (0.5 <= power < 0.999):
        return {"error": "d>0, 0<α<0.5, 0.5≤poder<0.999."}
    za = stats.norm.ppf(1 - alpha / 2)
    zb = stats.norm.ppf(power)
    n1 = 2 * ((za + zb) ** 2) / (effect_d ** 2)
    n1 = n1 * (1 + ratio) / 2 / max(ratio, 1e-9) if ratio != 1 else n1
    n1 = max(int(math.ceil(n1)), 2)
    n2 = max(int(math.ceil(n1 * ratio)), 2)
    return {"n_per_group_1": n1, "n_per_group_2": n2,
            "effect_d": effect_d, "alpha": alpha, "power": power,
            "explanation": f"Con d = {effect_d}, α = {alpha} y potencia = {power}, "
                           f"se necesitan ~{n1} sujetos por grupo para detectar la diferencia."}


def analyze_dataset(csv_text: str, group_col: Optional[str] = None,
                    value_col: Optional[str] = None) -> dict:
    """Exploración automática: resumen por columna, matriz de correlación,
    normalidad y contraste entre grupos si se indican columnas."""
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    rows = list(reader)
    if not rows:
        return {"error": "CSV vacío o sin encabezado."}
    columns: dict[str, list] = {}
    for name in reader.fieldnames:
        vals = []
        for row in rows:
            raw = (row.get(name) or "").strip()
            try:
                vals.append(float(raw))
            except ValueError:
                vals.append(None)
        numeric = [v for v in vals if v is not None]
        if len(numeric) >= max(2, 0.7 * len(rows)):
            columns[name] = vals
        else:
            columns[name] = None
    result = {"n_rows": len(rows), "columns_detected": list(columns.keys()),
              "numeric_columns": [k for k, v in columns.items() if v],
              "categorical_columns": [k for k, v in columns.items() if v is None],
              "summaries": {}, "correlations": {}, "group_test": None}
    for name, vals in columns.items():
        if vals:
            result["summaries"][name] = summary(vals)
    nums = [k for k, v in columns.items() if v]
    for i, a in enumerate(nums):
        for b in nums[i + 1:]:
            va, vb = columns[a], columns[b]
            pairs = [(x, y) for x, y in zip(va, vb) if x is not None and y is not None]
            if len(pairs) >= 3:
                xa, yb = [p[0] for p in pairs], [p[1] for p in pairs]
                r = correlation(xa, yb)
                if "error" not in r:
                    result["correlations"][f"{a} ~ {b}"] = {
                        "r": r["r"], "p": r["p"], "apa": r["apa"]}
    if group_col and value_col:
        groups: dict[str, list] = {}
        for row in rows:
            g = (row.get(group_col) or "").strip()
            raw = (row.get(value_col) or "").strip()
            try:
                v = float(raw)
            except ValueError:
                continue
            groups.setdefault(g, []).append(v)
        unique_groups = {k: v for k, v in groups.items() if len(v) >= 2}
        if len(unique_groups) == 2:
            (k1, v1), (k2, v2) = unique_groups.items()
            result["group_test"] = {"groups": [k1, k2], "ttest": ttest(v1, v2),
                                    "mannwhitney": mannwhitney(v1, v2)}
        elif len(unique_groups) > 2:
            result["group_test"] = {"groups": list(unique_groups.keys()),
                                    "anova": anova(unique_groups)}
        else:
            result["group_test"] = {"error": "Grupos insuficientes o vacíos."}
    return result
