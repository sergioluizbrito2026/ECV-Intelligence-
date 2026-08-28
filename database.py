import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "ecv_intelligence.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()
    conn.close()

def seed_database():
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM ecvs").fetchone()[0]
    if count == 0:
        ecvs = [
            ("ECV Alpha", "São Paulo", "SP", "Ativa", 1800),
            ("ECV Beta", "Campinas", "SP", "Ativa", 1500),
            ("ECV Central", "Santos", "SP", "Ativa", 1300),
            ("ECV Norte", "Guarulhos", "SP", "Ativa", 1200),
            ("ECV Sul", "Santo André", "SP", "Ativa", 1100),
            ("ECV Paulista", "São Paulo", "SP", "Ativa", 1700),
            ("ECV Leste", "São Paulo", "SP", "Ativa", 1400),
            ("ECV Oeste", "Osasco", "SP", "Ativa", 1250),
        ]
        conn.executemany(
            "INSERT INTO ecvs (nome,cidade,estado,status,meta_mensal) VALUES (?,?,?,?,?)",
            ecvs
        )

    vcount = conn.execute("SELECT COUNT(*) FROM vistorias").fetchone()[0]
    if vcount == 0:
        from data.generate_data import generate_vistorias
        generate_vistorias(conn, 5000)

    ucount = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    if ucount == 0:
        conn.executemany(
            "INSERT INTO usuarios (nome,email,perfil) VALUES (?,?,?)",
            [
                ("Administrador", "admin@ecv.local", "Administrador"),
                ("Analista", "analista@ecv.local", "Analista"),
            ],
        )
    conn.commit()
    conn.close()
