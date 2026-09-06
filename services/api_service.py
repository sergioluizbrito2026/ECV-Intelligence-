"""
ECV Intelligence V3
api_service.py

API REST da plataforma ECV Intelligence.

Responsabilidades:
- Health check
- Indicadores executivos
- ECVs
- Vistorias
- Desempenho por ECV
- Qualidade dos dados
- Automações
- Dataset para Power BI
- Estrutura preparada para SaaS

Executar:

uvicorn api_service:app --host 0.0.0.0 --port 8000
"""

from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import pandas as pd

from database.database import (
    init_db,
    seed_database,
    get_connection,
)

from services.analytics import (
    get_kpis,
    get_ecv_performance,
    get_quality_report,
    get_daily_series,
)

from services.automation import (
    AutomationEngine,
)


# ============================================================
# CONFIGURAÇÃO
# ============================================================

API_VERSION = "3.0.0"


# ============================================================
# DATABASE
# ============================================================

init_db()
seed_database()


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="ECV Intelligence API",
    description=(
        "API de inteligência operacional para "
        "Empresas Credenciadas de Vistoria."
    ),
    version=API_VERSION,
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# UTILITÁRIOS
# ============================================================

def _rows_to_dict(rows, columns):
    return [
        dict(zip(columns, row))
        for row in rows
    ]


def _query_df(query, params=()):
    """
    Executa consulta SQL e devolve DataFrame.
    """

    conn = get_connection()

    try:
        return pd.read_sql_query(
            query,
            conn,
            params=params,
        )

    finally:
        conn.close()


def _limit(value, minimum=1, maximum=5000):
    return min(
        max(int(value), minimum),
        maximum,
    )


# ============================================================
# HEALTH
# ============================================================

@app.get(
    "/health",
    tags=["Sistema"],
)
def health():

    return {
        "status": "ok",
        "service": "ECV Intelligence API",
        "version": API_VERSION,
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================
# STATUS
# ============================================================

@app.get(
    "/status",
    tags=["Sistema"],
)
def status():

    try:

        conn = get_connection()

        try:
            total_ecvs = conn.execute(
                "SELECT COUNT(*) FROM ecvs"
            ).fetchone()[0]

            total_vistorias = conn.execute(
                "SELECT COUNT(*) FROM vistorias"
            ).fetchone()[0]

        finally:
            conn.close()

        return {
            "api": "operational",
            "database": "operational",
            "ecvs": total_ecvs or 0,
            "vistorias": total_vistorias or 0,
            "version": API_VERSION,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ============================================================
# ECVs
# ============================================================

@app.get(
    "/ecvs",
    tags=["ECVs"],
)
def ecvs(
    limit: int = Query(
        100,
        ge=1,
        le=5000,
    )
):

    conn = get_connection()

    try:

        cursor = conn.execute(
            """
            SELECT
                id,
                nome,
                cidade,
                estado,
                status,
                meta_mensal
            FROM ecvs
            ORDER BY nome
            LIMIT ?
            """,
            (
                _limit(
                    limit,
                    1,
                    5000,
                ),
            ),
        )

        rows = cursor.fetchall()

        columns = [
            description[0]
            for description
            in cursor.description
        ]

        return _rows_to_dict(
            rows,
            columns,
        )

    finally:

        conn.close()


# ============================================================
# ECV INDIVIDUAL
# ============================================================

@app.get(
    "/ecvs/{ecv_id}",
    tags=["ECVs"],
)
def ecv_detail(ecv_id: int):

    conn = get_connection()

    try:

        row = conn.execute(
            """
            SELECT
                id,
                nome,
                cidade,
                estado,
                status,
                meta_mensal
            FROM ecvs
            WHERE id = ?
            """,
            (ecv_id,),
        ).fetchone()

        if not row:

            raise HTTPException(
                status_code=404,
                detail="ECV não encontrada.",
            )

        columns = [
            description[0]
            for description
            in conn.execute(
                """
                SELECT
                    id,
                    nome,
                    cidade,
                    estado,
                    status,
                    meta_mensal
                FROM ecvs
                WHERE id = ?
                """,
                (ecv_id,),
            ).description
        ]

        return dict(
            zip(
                columns,
                row,
            )
        )

    finally:

        conn.close()


# ============================================================
# VISTORIAS
# ============================================================

@app.get(
    "/vistorias",
    tags=["Vistorias"],
)
def vistorias(
    limit: int = Query(
        5000,
        ge=1,
        le=50000,
        description="Quantidade máxima de registros retornados",
    ),

    # Busca geral
    busca: Optional[str] = Query(
        None,
        description="Busca por placa ou ID da vistoria",
    ),

    # Filtros
    vistoria_id: Optional[int] = Query(
        None,
        description="ID da vistoria",
    ),

    placa: Optional[str] = Query(
        None,
        description="Placa do veículo",
    ),

    ecv: Optional[str] = Query(
        None,
        description="Nome ou parte do nome da ECV",
    ),

    cidade: Optional[str] = Query(
        None,
        description="Cidade da ECV",
    ),

    tipo: Optional[str] = Query(
        None,
        description="Tipo da vistoria",
    ),

    resultado: Optional[str] = Query(
        None,
        description="Resultado da vistoria",
    ),

    data_inicio: Optional[str] = Query(
        None,
        description="Data inicial YYYY-MM-DD",
    ),

    data_fim: Optional[str] = Query(
        None,
        description="Data final YYYY-MM-DD",
    ),
):

    # --------------------------------------------------------
    # QUERY BASE
    # --------------------------------------------------------

    query = """
        SELECT
            v.id,
            e.id AS ecv_id,
            e.nome AS ecv,
            e.cidade,
            e.estado,
            v.placa,
            v.tipo_vistoria,
            v.data_vistoria,
            v.resultado,
            v.tempo_minutos,
            v.valor
        FROM vistorias v
        INNER JOIN ecvs e
            ON e.id = v.ecv_id
        WHERE 1 = 1
    """

    params = []

    # --------------------------------------------------------
    # ID
    # --------------------------------------------------------

    if vistoria_id is not None:

        query += """
            AND v.id = ?
        """

        params.append(vistoria_id)

    # --------------------------------------------------------
    # BUSCA GERAL
    # Placa OU ID
    # --------------------------------------------------------

    if busca:

        busca = busca.strip()

        query += """
            AND (
                CAST(v.id AS TEXT) LIKE ?
                OR LOWER(COALESCE(v.placa, ''))
                    LIKE LOWER(?)
            )
        """

        termo = f"%{busca}%"

        params.extend([
            termo,
            termo,
        ])

    # --------------------------------------------------------
    # PLACA
    # --------------------------------------------------------

    if placa:

        query += """
            AND LOWER(COALESCE(v.placa, ''))
                LIKE LOWER(?)
        """

        params.append(
            f"%{placa.strip()}%"
        )

    # --------------------------------------------------------
    # ECV
    # --------------------------------------------------------

    if ecv:

        query += """
            AND LOWER(COALESCE(e.nome, ''))
                LIKE LOWER(?)
        """

        params.append(
            f"%{ecv.strip()}%"
        )

    # --------------------------------------------------------
    # CIDADE
    # --------------------------------------------------------

    if cidade:

        query += """
            AND LOWER(COALESCE(e.cidade, ''))
                LIKE LOWER(?)
        """

        params.append(
            f"%{cidade.strip()}%"
        )

    # --------------------------------------------------------
    # TIPO
    # --------------------------------------------------------

    if tipo:

        query += """
            AND LOWER(COALESCE(v.tipo_vistoria, ''))
                LIKE LOWER(?)
        """

        params.append(
            f"%{tipo.strip()}%"
        )

    # --------------------------------------------------------
    # RESULTADO
    # --------------------------------------------------------

    if resultado:

        query += """
            AND LOWER(COALESCE(v.resultado, ''))
                = LOWER(?)
        """

        params.append(
            resultado.strip()
        )

    # --------------------------------------------------------
    # DATA INICIAL
    # --------------------------------------------------------

    if data_inicio:

        # Validação da data
        try:

            datetime.strptime(
                data_inicio,
                "%Y-%m-%d",
            )

        except ValueError:

            raise HTTPException(
                status_code=400,
                detail=(
                    "data_inicio inválida. "
                    "Use o formato YYYY-MM-DD."
                ),
            )

        query += """
            AND DATE(v.data_vistoria) >= DATE(?)
        """

        params.append(
            data_inicio
        )

    # --------------------------------------------------------
    # DATA FINAL
    # --------------------------------------------------------

    if data_fim:

        try:

            datetime.strptime(
                data_fim,
                "%Y-%m-%d",
            )

        except ValueError:

            raise HTTPException(
                status_code=400,
                detail=(
                    "data_fim inválida. "
                    "Use o formato YYYY-MM-DD."
                ),
            )

        query += """
            AND DATE(v.data_vistoria) <= DATE(?)
        """

        params.append(
            data_fim
        )

    # --------------------------------------------------------
    # ORDENAÇÃO + LIMITE
    # --------------------------------------------------------

    query += """
        ORDER BY
            DATE(v.data_vistoria) DESC,
            v.id DESC
        LIMIT ?
    """

    params.append(
        _limit(
            limit,
            1,
            50000,
        )
    )

    # --------------------------------------------------------
    # EXECUÇÃO
    # --------------------------------------------------------

    df = _query_df(
        query,
        tuple(params),
    )

    # --------------------------------------------------------
    # RESPOSTA
    # --------------------------------------------------------

    return {
        "data": df.to_dict(
            orient="records"
        ),
        "total": len(df),
        "limit": _limit(
            limit,
            1,
            50000,
        ),
        "filtros": {
            "busca": busca,
            "vistoria_id": vistoria_id,
            "placa": placa,
            "ecv": ecv,
            "cidade": cidade,
            "tipo": tipo,
            "resultado": resultado,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
        },
    }


# ============================================================
# INDICADORES
# ============================================================

@app.get(
    "/indicadores",
    tags=["Analytics"],
)
def indicadores():

    df = _query_df(
        """
        SELECT
            v.id,
            e.nome AS ecv,
            v.placa,
            v.tipo_vistoria,
            v.data_vistoria,
            v.resultado,
            v.tempo_minutos,
            v.valor
        FROM vistorias v
        JOIN ecvs e
            ON e.id = v.ecv_id
        """
    )

    kpis = get_kpis(
        df
    )

    return {
        "total_vistorias": kpis[
            "total"
        ],
        "aprovadas": kpis[
            "aprovadas"
        ],
        "reprovadas": kpis[
            "reprovadas"
        ],
        "taxa_aprovacao": kpis[
            "taxa_aprovacao"
        ],
        "taxa_reprovacao": kpis[
            "taxa_reprovacao"
        ],
        "tempo_medio_minutos": kpis[
            "tempo_medio"
        ],
        "faturamento": kpis[
            "faturamento"
        ],
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================
# DESEMPENHO POR ECV
# ============================================================

@app.get(
    "/analytics/ecvs",
    tags=["Analytics"],
)
def analytics_ecvs():

    df = _query_df(
        """
        SELECT
            v.id,
            e.nome AS ecv,
            v.resultado,
            v.tempo_minutos,
            v.valor
        FROM vistorias v
        JOIN ecvs e
            ON e.id = v.ecv_id
        """
    )

    performance = get_ecv_performance(
        df
    )

    return performance.to_dict(
        orient="records"
    )


# ============================================================
# QUALIDADE
# ============================================================

@app.get(
    "/analytics/quality",
    tags=["Analytics"],
)
def analytics_quality():

    df = _query_df(
        """
        SELECT
            v.id,
            e.nome AS ecv,
            v.placa,
            v.tipo_vistoria,
            v.data_vistoria,
            v.resultado,
            v.tempo_minutos,
            v.valor
        FROM vistorias v
        JOIN ecvs e
            ON e.id = v.ecv_id
        """
    )

    return get_quality_report(
        df
    )


# ============================================================
# SÉRIE DIÁRIA
# ============================================================

@app.get(
    "/analytics/daily",
    tags=["Analytics"],
)
def analytics_daily():

    df = _query_df(
        """
        SELECT
            v.id,
            v.data_vistoria
        FROM vistorias v
        """
    )

    series = get_daily_series(
        df
    )

    return series.to_dict(
        orient="records"
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.get(
    "/dashboard",
    tags=["Analytics"],
)
def dashboard():

    df = _query_df(
        """
        SELECT
            v.id,
            e.nome AS ecv,
            v.placa,
            v.tipo_vistoria,
            v.data_vistoria,
            v.resultado,
            v.tempo_minutos,
            v.valor
        FROM vistorias v
        JOIN ecvs e
            ON e.id = v.ecv_id
        """
    )

    kpis = get_kpis(
        df
    )

    performance = get_ecv_performance(
        df
    )

    quality = get_quality_report(
        df
    )

    return {
        "kpis": kpis,
        "quality": quality,
        "ecvs": performance.to_dict(
            orient="records"
        ),
        "updated_at": datetime.now().isoformat(),
    }


# ============================================================
# AUTOMAÇÕES
# ============================================================

@app.get(
    "/automations",
    tags=["Automação"],
)
def automations():

    df = _query_df(
        """
        SELECT
            v.id,
            e.nome AS ecv,
            v.placa,
            v.tipo_vistoria,
            v.data_vistoria,
            v.resultado,
            v.tempo_minutos,
            v.valor
        FROM vistorias v
        JOIN ecvs e
            ON e.id = v.ecv_id
        """
    )

    engine = AutomationEngine()

    events = engine.evaluate(
        df
    )

    return {
        "total": len(events),
        "events": events,
    }


# ============================================================
# POWER BI
# ============================================================

@app.get(
    "/powerbi/vistorias",
    tags=["Power BI"],
)
def powerbi_vistorias(
    limit: int = Query(
        5000,
        ge=1,
        le=50000,
    ),
):

    query = """
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
        JOIN ecvs e
            ON e.id = v.ecv_id
        ORDER BY
            v.data_vistoria DESC,
            v.id DESC
        LIMIT ?
    """

    df = _query_df(
        query,
        (
            _limit(
                limit,
                1,
                50000,
            ),
        ),
    )

    return {
        "dataset": "vistorias",
        "version": API_VERSION,
        "rows": len(df),
        "data": df.to_dict(
            orient="records"
        ),
    }


# ============================================================
# POWER BI — ECVs
# ============================================================

@app.get(
    "/powerbi/ecvs",
    tags=["Power BI"],
)
def powerbi_ecvs():

    df = _query_df(
        """
        SELECT
            id AS ecv_id,
            nome AS ecv,
            cidade,
            estado,
            status,
            meta_mensal
        FROM ecvs
        ORDER BY nome
        """
    )

    return {
        "dataset": "ecvs",
        "version": API_VERSION,
        "rows": len(df),
        "data": df.to_dict(
            orient="records"
        ),
    }


# ============================================================
# POWER BI — INDICADORES
# ============================================================

@app.get(
    "/powerbi/indicadores",
    tags=["Power BI"],
)
def powerbi_indicadores():

    df = _query_df(
        """
        SELECT
            v.id,
            e.nome AS ecv,
            v.placa,
            v.tipo_vistoria,
            v.data_vistoria,
            v.resultado,
            v.tempo_minutos,
            v.valor
        FROM vistorias v
        JOIN ecvs e
            ON e.id = v.ecv_id
        """
    )

    kpis = get_kpis(
        df
    )

    performance = get_ecv_performance(
        df
    )

    return {
        "dataset": "indicadores",
        "version": API_VERSION,
        "kpis": kpis,
        "ecvs": performance.to_dict(
            orient="records"
        ),
    }


# ============================================================
# ROOT
# ============================================================

@app.get(
    "/",
    tags=["Sistema"],
)
def root():

    return {
        "name": "ECV Intelligence",
        "description": (
            "Plataforma SaaS de inteligência "
            "operacional para ECVs."
        ),
        "version": API_VERSION,
        "status": "online",
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "dashboard": "/dashboard",
            "ecvs": "/ecvs",
            "vistorias": "/vistorias",
            "indicadores": "/indicadores",
            "analytics_ecvs": "/analytics/ecvs",
            "analytics_quality": "/analytics/quality",
            "analytics_daily": "/analytics/daily",
            "automations": "/automations",
            "powerbi_vistorias": "/powerbi/vistorias",
            "powerbi_ecvs": "/powerbi/ecvs",
            "powerbi_indicadores": "/powerbi/indicadores",
            "docs": "/docs",
        },
    }
