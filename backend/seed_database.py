"""Resiembra forzada de la base de datos GENOMIND."""
from database import init_db

if __name__ == "__main__":
    seeded = init_db(force=True)
    print("Base de datos resembrada." if seeded else "Base de datos actualizada.")
