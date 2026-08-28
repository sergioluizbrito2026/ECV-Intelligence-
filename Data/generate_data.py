import random
from datetime import date, timedelta

TIPOS = [
    "Transferência",
    "Primeiro Emplacamento",
    "Regularização",
    "Segunda Via",
    "Alteração de Característica",
]

def fake_plate(i):
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return f"{letters[(i*7)%26]}{letters[(i*11)%26]}{letters[(i*13)%26]}-{1000 + (i % 9000)}"

def generate_vistorias(conn, n=5000):
    ecv_ids = [r[0] for r in conn.execute("SELECT id FROM ecvs").fetchall()]
    start = date.today() - timedelta(days=89)
    rows = []

    random.seed(42)
    for i in range(1, n + 1):
        ecv_id = random.choice(ecv_ids)
        d = start + timedelta(days=random.randint(0, 89))
        tipo = random.choice(TIPOS)
        # Pequenas diferenças por unidade para tornar a análise interessante.
        base = random.random()
        if ecv_id in (5, 8):
            resultado = "Reprovado" if base < 0.20 else ("Pendente" if base < 0.25 else "Aprovado")
        elif ecv_id == 1:
            resultado = "Reprovado" if base < 0.06 else ("Pendente" if base < 0.10 else "Aprovado")
        else:
            resultado = "Reprovado" if base < 0.12 else ("Pendente" if base < 0.16 else "Aprovado")

        tempo = max(7, round(random.gauss(21, 6), 1))
        valor = round(random.choice([95, 110, 120, 135, 150]), 2)
        rows.append((
            ecv_id, fake_plate(i), tipo, d.isoformat(),
            resultado, tempo, valor
        ))

    conn.executemany("""
        INSERT INTO vistorias
        (ecv_id, placa, tipo_vistoria, data_vistoria, resultado, tempo_minutos, valor)
        VALUES (?,?,?,?,?,?,?)
    """, rows)
    conn.commit()
    return len(rows)

if __name__ == "__main__":
    from database.database import get_connection, init_db
    init_db()
    conn = get_connection()
    print(f"Gerados: {generate_vistorias(conn, 5000)}")
    conn.close()
