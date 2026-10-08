"""Capa de base de datos GENOMIND: SQLite embebida con seed automático."""
import json
import sqlite3
from pathlib import Path
from typing import Any, Iterator

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "genomind.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS diseases (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    name_es TEXT NOT NULL,
    category TEXT NOT NULL,
    baseline_risk REAL NOT NULL,
    baseline_label TEXT NOT NULL,
    description_es TEXT NOT NULL,
    modifiable TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS snps (
    rsid TEXT NOT NULL,
    gene TEXT NOT NULL,
    chromosome TEXT,
    disease TEXT NOT NULL REFERENCES diseases(code),
    risk_allele TEXT NOT NULL,
    other_allele TEXT NOT NULL,
    odds_ratio REAL NOT NULL,
    risk_allele_freq REAL NOT NULL,
    p_value TEXT,
    study TEXT,
    note TEXT,
    PRIMARY KEY (rsid, disease)
);
CREATE TABLE IF NOT EXISTS foods (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    kcal REAL, protein_g REAL, carbs_g REAL, fat_g REAL, fiber_g REAL,
    glycemic_index REAL, sodium_mg REAL, potassium_mg REAL, sugar_g REAL,
    cost_index INTEGER, water_l REAL, region TEXT, note TEXT
);
CREATE TABLE IF NOT EXISTS regions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    pm25 REAL, green_pct REAL, walkability REAL, healthcare_index REAL,
    life_expectancy REAL, ncd_per100k REAL, note TEXT
);
CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    genotypes TEXT NOT NULL,
    lifestyle TEXT NOT NULL,
    results TEXT
);
CREATE INDEX IF NOT EXISTS idx_snps_disease ON snps(disease);
CREATE INDEX IF NOT EXISTS idx_foods_category ON foods(category);
"""


def _load_json(filename: str) -> Any:
    with open(DATA_DIR / filename, encoding="utf-8") as fh:
        return json.load(fh)


def get_conn(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(force: bool = False, db_path: Path = DB_PATH) -> bool:
    """Crea el esquema y siembra los datos si la base está vacía.

    Devuelve True si se sembraron datos.
    """
    conn = get_conn(db_path)
    try:
        conn.executescript(SCHEMA)
        if force:
            for table in ("diseases", "snps", "foods", "regions"):
                conn.execute(f"DELETE FROM {table}")
            conn.commit()
        seeded = False
        if conn.execute("SELECT COUNT(*) FROM diseases").fetchone()[0] == 0:
            for row in _load_json("diseases.json"):
                conn.execute(
                    "INSERT INTO diseases VALUES (?,?,?,?,?,?,?,?)",
                    (row["code"], row["name"], row["name_es"], row["category"],
                     row["baseline_risk"], row["baseline_label"],
                     row["description_es"], json.dumps(row["modifiable"])),
                )
            seeded = True
        if conn.execute("SELECT COUNT(*) FROM snps").fetchone()[0] == 0:
            for row in _load_json("snps.json"):
                conn.execute(
                    "INSERT INTO snps VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (row["rsid"], row["gene"], row.get("chromosome"), row["disease"],
                     row["risk_allele"], row["other_allele"], row["odds_ratio"],
                     row["risk_allele_freq"], row.get("p_value"), row.get("study"),
                     row.get("note")),
                )
            seeded = True
        if conn.execute("SELECT COUNT(*) FROM foods").fetchone()[0] == 0:
            for row in _load_json("foods.json"):
                conn.execute(
                    "INSERT INTO foods VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (row["id"], row["name"], row["category"], row["kcal"], row["protein_g"],
                     row["carbs_g"], row["fat_g"], row["fiber_g"], row["glycemic_index"],
                     row["sodium_mg"], row["potassium_mg"], row["sugar_g"], row["cost_index"],
                     row["water_l"], row["region"], row["note"]),
                )
            seeded = True
        if conn.execute("SELECT COUNT(*) FROM regions").fetchone()[0] == 0:
            for row in _load_json("regions.json"):
                conn.execute(
                    "INSERT INTO regions VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (row["id"], row["name"], row["country"], row["pm25"], row["green_pct"],
                     row["walkability"], row["healthcare_index"], row["life_expectancy"],
                     row["ncd_per100k"], row["note"]),
                )
            seeded = True
        conn.commit()
        return seeded
    finally:
        conn.close()


def rows_as_dicts(cursor: sqlite3.Cursor) -> Iterator[dict]:
    for row in cursor:
        yield dict(row)
