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
- Estrutura preparada para SaaS multi-tenant

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

API_VERSION = "3.1.0"

DEFAULT_LIMIT = 5000
MAX_LIMIT = 50000


# ============================================================
# DATABASE
# ============================================================

try:
    init_db()
    seed_database()
except Exception as exc:
    print(
        f"[DATABASE] Erro ao inicializar banco: {exc}"
    )


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
    """
    Converte linhas SQLite em lista de dicionários.
    """

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


def _limit(
    value,
    minimum=1,
    maximum=MAX_LIMIT,
):
    """
    Garante que o limite esteja dentro
    de uma faixa segura.
    """

    try:
        value = int(value)
    except Exception:
        value = minimum

    return min(
        max(value, minimum),
        maximum,
    )


def _safe_records(df):
    """
    Converte DataFrame em registros JSON
    sem valores NaN incompatíveis.
    """

    if df is None or df.empty:
        return []

    result = df.copy()

    result = result.where(
        pd.notna(result),
        None,
    )

    return result.to_dict(
        orient="records"
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

    conn = None

    try:

        conn = get_connection()

        total_ecvs = conn.execute(
            """
            SELECT COUNT(*)
            FROM ecvs
            """
        ).fetchone()[0]

        total_vistorias = conn.execute(
            """
            SELECT COUNT(*)
            FROM vistorias
            """
        ).fetchone()[0]

        total_usuarios = conn.execute(
            """
            SELECT COUNT(*)
            FROM usuarios
            """
        ).fetchone()[0]

        return {
            "api": "operational",
            "database": "operational",
            "ecvs": total_ecvs or 0,
            "vistorias": total_vistorias or 0,
            "usuarios": total_usuarios or 0,
            "version": API_VERSION,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Erro no banco de dados: {exc}",
        )

    finally:

        if conn is not None:
            conn.close()


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
        le=MAX_LIMIT,
    )
):

    conn = None

    try:

        conn = get_connection()

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
                    MAX_LIMIT,
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

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Erro ao consultar ECVs: {exc}",
        )

    finally:

        if conn is not None:
            conn.close()


# ============================================================
# ECV INDIVIDUAL
# ============================================================

@app.get(
    "/ecvs/{ecv_id}",
    tags=["ECVs"],
)
def ecv_detail(
    ecv_id: int,
):

    conn = None

    try:

        conn = get_connection()

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
            WHERE id = ?
            """,
            (ecv_id,),
        )

        row = cursor.fetchone()

        if not row:

            raise HTTPException(
                status_code=404,
                detail="ECV não encontrada.",
            )

        columns = [
            description[0]
            for description
            in cursor.description
        ]

        return dict(
            zip(
                columns,
                row,
            )
        )

    except HTTPException:

        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Erro ao consultar ECV: {exc}",
        )

    finally:

        if conn is not None:
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
        DEFAULT_LIMIT,
        ge=1,
        le=MAX_LIMIT,
        description="Quantidade máxima de registros retornados",
    ),

    busca: Optional[str] = Query(
        None,
        description="Busca por placa ou ID da vistoria",
    ),

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
    #
    # IMPORTANTE:
    # No database.py a coluna é "tipo".
    # Portanto usamos:
    #
    # v.tipo AS tipo_vistoria
    # --------------------------------------------------------

    query = """
        SELECT
            v.id,
            e.id AS ecv_id,
            e.nome AS ecv,
            e.cidade,
            e.estado,
            v.placa,
            v.tipo AS tipo_vistoria,
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

        params.append(
            vistoria_id
        )

    # --------------------------------------------------------
    # BUSCA
    # --------------------------------------------------------

    if busca:

        busca = busca.strip()

        if busca:

            query += """
                AND (
                    CAST(v.id AS TEXT) LIKE ?
                    OR LOWER(
                        COALESCE(v.placa, '')
                    ) LIKE LOWER(?)
                )
            """

            termo = f"%{busca}%"

            params.extend(
                [
                    termo,
                    termo,
                ]
            )

    # --------------------------------------------------------
    # PLACA
    # --------------------------------------------------------

    if placa:

        placa_limpa = placa.strip()

        if placa_limpa:

            query += """
                AND LOWER(
                    COALESCE(v.placa, '')
                ) LIKE LOWER(?)
            """

            params.append(
                f"%{placa_limpa}%"
            )

    # --------------------------------------------------------
    # ECV
    # --------------------------------------------------------

    if ecv:

        ecv_limpa = ecv.strip()

        if ecv_limpa:

            query += """
                AND LOWER(
                    COALESCE(e.nome, '')
                ) LIKE LOWER(?)
            """

            params.append(
                f"%{ecv_limpa}%"
            )

    # --------------------------------------------------------
    # CIDADE
    # --------------------------------------------------------

    if cidade:

        cidade_limpa = cidade.strip()

        if cidade_limpa:

            query += """
                AND LOWER(
                    COALESCE(e.cidade, '')
                ) LIKE LOWER(?)
            """

            params.append(
                f"%{cidade_limpa}%"
            )

    # --------------------------------------------------------
    # TIPO
    # --------------------------------------------------------

    if tipo:

        tipo_limpo = tipo.strip()

        if tipo_limpo:

            query += """
                AND LOWER(
                    COALESCE(v.tipo, '')
                ) LIKE LOWER(?)
            """

            params.append(
                f"%{tipo_limpo}%"
            )

    # --------------------------------------------------------
    # RESULTADO
    # --------------------------------------------------------

    if resultado:

        resultado_limpo = resultado.strip()

        if resultado_limpo:

            query += """
                AND LOWER(
                    COALESCE(v.resultado, '')
                ) = LOWER(?)
            """

            params.append(
                resultado_limpo
            )

    # --------------------------------------------------------
    # DATA INICIAL
    # --------------------------------------------------------

    if data_inicio:

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
            AND DATE(v.data_vistoria)
                >= DATE(?)
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
            AND DATE(v.data_vistoria)
                <= DATE(?)
        """

        params.append(
            data_fim
        )

    # --------------------------------------------------------
    # ORDENAÇÃO
    # --------------------------------------------------------

    query += """
        ORDER BY
            datetime(v.data_vistoria) DESC,
            v.id DESC
        LIMIT ?
    """

    final_limit = _limit(
        limit,
        1,
        MAX_LIMIT,
    )

    params.append(
        final_limit
    )

    # --------------------------------------------------------
    # EXECUÇÃO
    # --------------------------------------------------------

    try:

        df = _query_df(
            query,
            tuple(params),
        )

    except Exception as exc:

        print(
            f"[VISTORIAS] Erro SQL: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Erro ao consultar vistorias: "
                f"{exc}"
            ),
        )

    # --------------------------------------------------------
    # RESPOSTA
    # --------------------------------------------------------

    return {
        "data": _safe_records(df),
        "total": len(df),
        "limit": final_limit,
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

    try:

        df = _query_df(
            """
            SELECT
                v.id,
                e.nome AS ecv,
                v.placa,
                v.tipo AS tipo_vistoria,
                v.data_vistoria,
                v.resultado,
                v.tempo_minutos,
                v.valor
            FROM vistorias v
            JOIN ecvs e
                ON e.id = v.ecv_id
            """
        )

        kpis = get_kpis(df)

        return {
            "total_vistorias": kpis.get(
                "total",
                0,
            ),
            "aprovadas": kpis.get(
                "aprovadas",
                0,
            ),
            "reprovadas": kpis.get(
                "reprovadas",
                0,
            ),
            "taxa_aprovacao": kpis.get(
                "taxa_aprovacao",
                0,
            ),
            "taxa_reprovacao": kpis.get(
                "taxa_reprovacao",
                0,
            ),
            "tempo_medio_minutos": kpis.get(
                "tempo_medio",
                0,
            ),
            "faturamento": kpis.get(
                "faturamento",
                0,
            ),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Erro nos indicadores: {exc}",
        )


# ============================================================
# DESEMPENHO POR ECV
# ============================================================

@app.get(
    "/analytics/ecvs",
    tags=["Analytics"],
)
def analytics_ecvs():

    try:

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

        return _safe_records(
            performance
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Erro na análise de performance: "
                f"{exc}"
            ),
        )


# ============================================================
# QUALIDADE
# ============================================================

@app.get(
    "/analytics/quality",
    tags=["Analytics"],
)
def analytics_quality():

    try:

        df = _query_df(
            """
            SELECT
                v.id,
                e.nome AS ecv,
                v.placa,
                v.tipo AS tipo_vistoria,
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

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Erro no relatório de qualidade: "
                f"{exc}"
            ),
        )


# ============================================================
# SÉRIE DIÁRIA
# ============================================================

@app.get(
    "/analytics/daily",
    tags=["Analytics"],
)
def analytics_daily():

    try:

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

        return _safe_records(
            series
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Erro na série diária: "
                f"{exc}"
            ),
        )


# ============================================================
# DASHBOARD
# ============================================================

@app.get(
    "/dashboard",
    tags=["Analytics"],
)
def dashboard():

    try:

        df = _query_df(
            """
            SELECT
                v.id,
                e.nome AS ecv,
                v.placa,
                v.tipo AS tipo_vistoria,
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
            "ecvs": _safe_records(
                performance
            ),
            "updated_at": datetime.now().isoformat(),
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Erro ao montar dashboard: "
                f"{exc}"
            ),
        )


# ============================================================
# AUTOMAÇÕES
# ============================================================

@app.get(
    "/automations",
    tags=["Automação"],
)
def automations():

    try:

        df = _query_df(
            """
            SELECT
                v.id,
                e.nome AS ecv,
                v.placa,
                v.tipo AS tipo_vistoria,
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

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Erro nas automações: "
                f"{exc}"
            ),
        )


# ============================================================
# POWER BI — VISTORIAS
# ============================================================

@app.get(
    "/powerbi/vistorias",
    tags=["Power BI"],
)
def powerbi_vistorias(
    limit: int = Query(
        DEFAULT_LIMIT,
        ge=1,
        le=MAX_LIMIT,
    ),
):

    try:

        query = """
            SELECT
                v.id AS vistoria_id,
                v.data_vistoria,
                e.id AS ecv_id,
                e.nome AS ecv,
                e.cidade,
                e.estado,
                v.placa,
                v.tipo AS tipo_vistoria,
                v.resultado,
                v.tempo_minutos,
                v.valor
            FROM vistorias v
            JOIN ecvs e
                ON e.id = v.ecv_id
            ORDER BY
                datetime(v.data_vistoria) DESC,
                v.id DESC
            LIMIT ?
        """

        df = _query_df(
            query,
            (
                _limit(
                    limit,
                    1,
                    MAX_LIMIT,
                ),
            ),
        )

        return {
            "dataset": "vistorias",
            "version": API_VERSION,
            "rows": len(df),
            "data": _safe_records(
                df
            ),
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Erro no dataset Power BI "
                "de vistorias: "
                f"{exc}"
            ),
        )


# ============================================================
# POWER BI — ECVs
# ============================================================

@app.get(
    "/powerbi/ecvs",
    tags=["Power BI"],
)
def powerbi_ecvs():

    try:

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
            "data": _safe_records(
                df
            ),
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Erro no dataset Power BI "
                "de ECVs: "
                f"{exc}"
            ),
        )


# ============================================================
# POWER BI — INDICADORES
# ============================================================

@app.get(
    "/powerbi/indicadores",
    tags=["Power BI"],
)
def powerbi_indicadores():

    try:

        df = _query_df(
            """
            SELECT
                v.id,
                e.nome AS ecv,
                v.placa,
                v.tipo AS tipo_vistoria,
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
            "ecvs": _safe_records(
                performance
            ),
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Erro nos indicadores "
                "do Power BI: "
                f"{exc}"
            ),
        )


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
            "ecv_detail": "/ecvs/{ecv_id}",
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
