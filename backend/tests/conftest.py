"""Configuración de pytest: raigambre de imports y base de datos."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
