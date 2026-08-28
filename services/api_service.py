from fastapi import FastAPI
from database.database import init_db, seed_database, get_connection

init_db()
seed_database()
app = FastAPI(title="ECV Intelligence API", version="1.0.0")

@app.get("/health")
def health():
    return {"status": "ok", "service": "ECV Intelligence API"}

@app.get("/ecvs")
def ecvs():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM ecvs").fetchall()
    cols = [d[0] for d in conn.execute("SELECT * FROM ecvs LIMIT 1").description]
    conn.close()
    return [dict(zip(cols, row)) for row in rows]

@app.get("/vistorias")
def vistorias(limit: int = 100):
    conn = get_connection()
    rows = conn.execute("""
        SELECT v.id, e.nome ecv, v.placa, v.tipo_vistoria,
               v.data_vistoria, v.resultado, v.tempo_minutos, v.valor
        FROM vistorias v JOIN ecvs e ON e.id = v.ecv_id
        ORDER BY v.data_vistoria DESC LIMIT ?
    """, (min(max(limit, 1), 1000),)).fetchall()
    cols = [d[0] for d in conn.execute("""
        SELECT v.id, e.nome ecv, v.placa, v.tipo_vistoria,
               v.data_vistoria, v.resultado, v.tempo_minutos, v.valor
        FROM vistorias v JOIN ecvs e ON e.id = v.ecv_id LIMIT 1
    """).description]
    conn.close()
    return [dict(zip(cols, row)) for row in rows]

@app.get("/indicadores")
def indicadores():
    conn = get_connection()
    total, approved, rejected, revenue, avg_time = conn.execute("""
        SELECT
            COUNT(*),
            SUM(CASE WHEN resultado='Aprovado' THEN 1 ELSE 0 END),
            SUM(CASE WHEN resultado='Reprovado' THEN 1 ELSE 0 END),
            SUM(valor),
            AVG(tempo_minutos)
        FROM vistorias
    """).fetchone()
    conn.close()
    return {
        "total_vistorias": total or 0,
        "aprovadas": approved or 0,
        "reprovadas": rejected or 0,
        "taxa_aprovacao": round((approved or 0) / total * 100, 2) if total else 0,
        "tempo_medio_minutos": round(avg_time or 0, 2),
        "faturamento": round(revenue or 0, 2),
    }
