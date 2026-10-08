"""Lanzador de GENOMIND: un solo comando para toda la plataforma."""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(BACKEND))

import webbrowser

import uvicorn

from main import app  # noqa: E402 (requiere backend en sys.path)


def main() -> None:
    url = "http://127.0.0.1:8000"
    print("=" * 56)
    print("  GENOMIND — Inteligencia Genómica Abierta v1.0.0")
    print("=" * 56)
    print(f"  Interfaz:    {url}")
    print(f"  API REST:    {url}/docs")
    print("  Cierra con Ctrl+C")
    print("=" * 56)
    webbrowser.open(url)
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


if __name__ == "__main__":
    main()
