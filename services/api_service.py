from datetime import datetime
from fastapi import FastAPI
from database.database import init_db, seed_database, get_connection
from google import genai
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


@app.get("/powerbi/vistorias")
def powerbi_vistorias(limit: int = 5000):
    """
    Dataset detalhado para consumo no Power BI.
    Mantém os dados em nível de vistoria para que o Power BI
    possa aplicar filtros, medidas DAX e segmentações.
    """
    conn = get_connection()
    try:
        cursor = conn.execute("""
            SELECT
                v.id AS vistoria_id,
                v.data_vistoria,
                e.id AS ecv_id,
                e.nome AS ecv,
                e.cidade,
                e.estado,
                v.placa,
                v.tipo_vistoria,
                v.resultado,
                v.tempo_minutos,
                v.valor
            FROM vistorias v
            JOIN ecvs e ON e.id = v.ecv_id
            ORDER BY v.data_vistoria DESC
            LIMIT ?
        """, (min(max(limit, 1), 50000),))

        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description]

        return {
            "dataset": "ecv_vistorias",
            "version": "2.0.0",
            "records": len(rows),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "data": [dict(zip(cols, row)) for row in rows],
        }
    finally:
        conn.close()


@app.get("/powerbi/indicadores")
def powerbi_indicadores():
    """
    KPIs prontos para cards e indicadores executivos no Power BI.
    """
    return indicadores()


@app.get("/integration/status")
def integration_status():
    """
    Status da camada de integração.
    """
    db_status = "online"
    try:
        conn = get_connection()
        conn.execute("SELECT 1").fetchone()
        conn.close()
    except Exception:
        db_status = "offline"

    return {
        "api": "online",
        "database": db_status,
        "power_bi_dataset": "/powerbi/vistorias",
        "power_bi_kpis": "/powerbi/indicadores",
        "swagger": "/docs",
        "openapi": "/openapi.json",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }

