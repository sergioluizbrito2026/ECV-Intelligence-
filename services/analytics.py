
"""
ECV Intelligence V3.1
services/analytics.py

Camada central de indicadores e inteligência operacional.

Responsabilidades:
- KPIs executivos
- séries temporais
- desempenho por ECV
- faturamento
- produtividade
- qualidade dos dados
- rankings
- tendências
- variações
- identificação de outliers
- indicadores para IA/LLM
- resumo executivo

Compatibilidade:
    app.py
    services/ai_service.py
    ECV Intelligence V3
"""

import re
from typing import Any, Dict, List

import pandas as pd


# ============================================================
# UTILITÁRIOS
# ============================================================

def _copy_df(df) -> pd.DataFrame:
    """
    Retorna uma cópia segura do DataFrame.
    """

    if df is None:
        return pd.DataFrame()

    if isinstance(df, pd.DataFrame):
        return df.copy()

    try:
        return pd.DataFrame(df).copy()
    except Exception:
        return pd.DataFrame()


def _numeric(series) -> pd.Series:
    """
    Converte uma série para valores numéricos.
    """

    return pd.to_numeric(
        series,
        errors="coerce",
    )


def _ensure_columns(
    df: pd.DataFrame,
    columns: List[str],
) -> pd.DataFrame:
    """
    Garante que as colunas existam.
    """

    for col in columns:

        if col not in df.columns:
            df[col] = pd.NA

    return df


def _safe_float(
    value: Any,
    default: float = 0.0,
) -> float:

    try:
        value = float(value)

        if pd.isna(value):
            return default

        return value

    except (
        TypeError,
        ValueError,
    ):
        return default


def _safe_int(
    value: Any,
    default: int = 0,
) -> int:

    try:
        return int(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def _normalize_text(value: Any) -> str:
    """
    Normaliza textos para comparações.
    """

    if pd.isna(value):
        return ""

    return (
        str(value)
        .strip()
        .lower()
    )


def _format_number(value: Any) -> str:
    """
    Formata números no padrão brasileiro.
    """

    try:

        return (
            f"{float(value):,.0f}"
            .replace(",", ".")
        )

    except (
        TypeError,
        ValueError,
    ):

        return "0"


def _format_money(value: Any) -> str:
    """
    Formata valores monetários.
    """

    try:

        return (
            f"R$ {float(value):,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    except (
        TypeError,
        ValueError,
    ):

        return "R$ 0,00"


def _empty_dataframe(columns):
    return pd.DataFrame(
        columns=columns
    )


# ============================================================
# KPIs EXECUTIVOS
# ============================================================

def get_kpis(df) -> Dict[str, Any]:
    """
    Calcula os principais KPIs operacionais.

    Retorna:

        total
        aprovadas
        reprovadas
        outros_resultados
        taxa_aprovacao
        taxa_reprovacao
        tempo_medio
        faturamento
        ticket_medio
        ecvs
    """

    df = _copy_df(df)

    if df.empty:

        return {
            "total": 0,
            "aprovadas": 0,
            "reprovadas": 0,
            "outros_resultados": 0,
            "taxa_aprovacao": 0.0,
            "taxa_reprovacao": 0.0,
            "tempo_medio": 0.0,
            "faturamento": 0.0,
            "ticket_medio": 0.0,
            "ecvs": 0,
        }

    _ensure_columns(
        df,
        [
            "ecv",
            "resultado",
            "tempo_minutos",
            "valor",
        ],
    )

    resultado = (
        df["resultado"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    aprovadas = int(
        resultado.eq("aprovado").sum()
    )

    reprovadas = int(
        resultado.eq("reprovado").sum()
    )

    total = int(len(df))

    outros = max(
        total
        - aprovadas
        - reprovadas,
        0,
    )

    tempo = _numeric(
        df["tempo_minutos"]
    )

    valor = _numeric(
        df["valor"]
    )

    faturamento = (
        float(valor.sum())
        if valor.notna().any()
        else 0.0
    )

    tempo_medio = (
        float(tempo.mean())
        if tempo.notna().any()
        else 0.0
    )

    ecvs = (
        df["ecv"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    ecvs = ecvs[
        ecvs != ""
    ]

    return {
        "total": total,
        "aprovadas": aprovadas,
        "reprovadas": reprovadas,
        "outros_resultados": outros,
        "taxa_aprovacao": round(
            aprovadas / total * 100,
            2,
        ) if total else 0.0,
        "taxa_reprovacao": round(
            reprovadas / total * 100,
            2,
        ) if total else 0.0,
        "tempo_medio": round(
            tempo_medio,
            2,
        ),
        "faturamento": round(
            faturamento,
            2,
        ),
        "ticket_medio": round(
            faturamento / total,
            2,
        ) if total else 0.0,
        "ecvs": int(
            ecvs.nunique()
        ),
    }


# ============================================================
# SÉRIE DIÁRIA
# ============================================================

def get_daily_series(df) -> pd.DataFrame:
    """
    Agrupa vistorias por dia.

    Retorna:
        data
        vistorias
        faturamento
        ticket_medio
    """

    df = _copy_df(df)

    columns = [
        "data",
        "vistorias",
        "faturamento",
        "ticket_medio",
    ]

    if df.empty:
        return _empty_dataframe(columns)

    _ensure_columns(
        df,
        [
            "data_vistoria",
            "valor",
        ],
    )

    dates = pd.to_datetime(
        df["data_vistoria"],
        errors="coerce",
    )

    work = pd.DataFrame(
        {
            "data": dates.dt.date,
            "valor": _numeric(
                df["valor"]
            ),
        }
    )

    work = work.dropna(
        subset=["data"]
    )

    if work.empty:
        return _empty_dataframe(columns)

    result = (
        work.groupby("data")
        .agg(
            vistorias=("data", "size"),
            faturamento=("valor", "sum"),
        )
        .reset_index()
    )

    result["ticket_medio"] = (
        result["faturamento"]
        /
        result["vistorias"]
        .replace(0, pd.NA)
    ).fillna(0)

    result["faturamento"] = (
        result["faturamento"]
        .fillna(0)
        .round(2)
    )

    result["ticket_medio"] = (
        result["ticket_medio"]
        .fillna(0)
        .round(2)
    )

    return (
        result
        .sort_values("data")
        .reset_index(drop=True)
    )


# ============================================================
# TENDÊNCIA OPERACIONAL
# ============================================================

def get_daily_trend(df) -> pd.DataFrame:
    """
    Calcula tendência diária de volume.

    Retorna:
        data
        vistorias
        variacao_percentual
        media_movel_7
    """

    daily = get_daily_series(df)

    if daily.empty:

        return pd.DataFrame(
            columns=[
                "data",
                "vistorias",
                "variacao_percentual",
                "media_movel_7",
            ]
        )

    daily = daily.copy()

    daily["variacao_percentual"] = (
        daily["vistorias"]
        .pct_change()
        .replace(
            [float("inf"), -float("inf")],
            pd.NA,
        )
        * 100
    )

    daily["variacao_percentual"] = (
        daily["variacao_percentual"]
        .fillna(0)
        .round(2)
    )

    daily["media_movel_7"] = (
        daily["vistorias"]
        .rolling(
            window=7,
            min_periods=1,
        )
        .mean()
        .round(2)
    )

    return daily[
        [
            "data",
            "vistorias",
            "variacao_percentual",
            "media_movel_7",
        ]
    ]


# ============================================================
# DESEMPENHO POR ECV
# ============================================================

def get_ecv_performance(df) -> pd.DataFrame:
    """
    Calcula indicadores por ECV.

    Retorna:
        ecv
        total
        aprovadas
        reprovadas
        taxa_aprovacao
        taxa_reprovacao
        tempo_medio
        faturamento
        ticket_medio
    """

    df = _copy_df(df)

    columns = [
        "ecv",
        "total",
        "aprovadas",
        "reprovadas",
        "taxa_aprovacao",
        "taxa_reprovacao",
        "tempo_medio",
        "faturamento",
        "ticket_medio",
    ]

    if df.empty:
        return _empty_dataframe(columns)

    _ensure_columns(
        df,
        [
            "ecv",
            "id",
            "resultado",
            "tempo_minutos",
            "valor",
        ],
    )

    work = df.copy()

    work["resultado_norm"] = (
        work["resultado"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    work["aprovado"] = (
        work["resultado_norm"]
        == "aprovado"
    )

    work["reprovado"] = (
        work["resultado_norm"]
        == "reprovado"
    )

    work["tempo_num"] = _numeric(
        work["tempo_minutos"]
    )

    work["valor_num"] = _numeric(
        work["valor"]
    )

    result = (
        work.groupby(
            "ecv",
            dropna=False,
        )
        .agg(
            total=("id", "count"),
            aprovadas=("aprovado", "sum"),
            reprovadas=("reprovado", "sum"),
            tempo_medio=("tempo_num", "mean"),
            faturamento=("valor_num", "sum"),
        )
        .reset_index()
    )

    result["taxa_aprovacao"] = (
        result["aprovadas"]
        /
        result["total"].replace(
            0,
            pd.NA,
        )
        * 100
    )

    result["taxa_reprovacao"] = (
        result["reprovadas"]
        /
        result["total"].replace(
            0,
            pd.NA,
        )
        * 100
    )

    result["ticket_medio"] = (
        result["faturamento"]
        /
        result["total"].replace(
            0,
            pd.NA,
        )
    )

    result["taxa_aprovacao"] = (
        result["taxa_aprovacao"]
        .fillna(0)
        .round(2)
    )

    result["taxa_reprovacao"] = (
        result["taxa_reprovacao"]
        .fillna(0)
        .round(2)
    )

    result["tempo_medio"] = (
        result["tempo_medio"]
        .fillna(0)
        .round(2)
    )

    result["faturamento"] = (
        result["faturamento"]
        .fillna(0)
        .round(2)
    )

    result["ticket_medio"] = (
        result["ticket_medio"]
        .fillna(0)
        .round(2)
    )

    return (
        result
        .sort_values(
            [
                "taxa_aprovacao",
                "total",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .reset_index(drop=True)
    )


# ============================================================
# RANKING DE ECV
# ============================================================

def get_ecv_ranking(
    df,
    metric: str = "taxa_aprovacao",
    ascending: bool = False,
) -> pd.DataFrame:
    """
    Retorna ranking das ECVs.

    Métricas suportadas:
        taxa_aprovacao
        taxa_reprovacao
        total
        faturamento
        ticket_medio
        tempo_medio
    """

    performance = get_ecv_performance(
        df
    )

    if performance.empty:
        return performance

    if metric not in performance.columns:
        metric = "taxa_aprovacao"

    return (
        performance
        .sort_values(
            metric,
            ascending=ascending,
        )
        .reset_index(drop=True)
    )


# ============================================================
# ECVs ABAIXO DA MÉDIA
# ============================================================

def get_ecvs_below_average(df) -> pd.DataFrame:
    """
    Identifica ECVs abaixo da média de aprovação.
    """

    performance = get_ecv_performance(
        df
    )

    if performance.empty:
        return performance

    media = _safe_float(
        performance[
            "taxa_aprovacao"
        ].mean()
    )

    result = performance[
        performance[
            "taxa_aprovacao"
        ] < media
    ].copy()

    result["diferenca_media"] = (
        result["taxa_aprovacao"]
        - media
    ).round(2)

    return (
        result
        .sort_values(
            "diferenca_media"
        )
        .reset_index(drop=True)
    )


# ============================================================
# DISTRIBUIÇÃO DE RESULTADOS
# ============================================================

def get_result_distribution(df) -> pd.DataFrame:

    df = _copy_df(df)

    columns = [
        "resultado",
        "quantidade",
        "percentual",
    ]

    if (
        df.empty
        or "resultado" not in df.columns
    ):
        return _empty_dataframe(columns)

    result = (
        df["resultado"]
        .fillna("Não informado")
        .astype(str)
        .str.strip()
        .replace("", "Não informado")
        .value_counts()
        .rename_axis("resultado")
        .reset_index(
            name="quantidade"
        )
    )

    total = int(
        result["quantidade"].sum()
    )

    result["percentual"] = (
        result["quantidade"]
        / total
        * 100
        if total
        else 0
    )

    result["percentual"] = (
        result["percentual"]
        .round(2)
    )

    return result


# ============================================================
# TIPOS DE VISTORIA
# ============================================================

def get_type_distribution(df) -> pd.DataFrame:

    df = _copy_df(df)

    columns = [
        "tipo_vistoria",
        "quantidade",
        "percentual",
    ]

    if (
        df.empty
        or "tipo_vistoria" not in df.columns
    ):
        return _empty_dataframe(columns)

    result = (
        df["tipo_vistoria"]
        .fillna("Não informado")
        .astype(str)
        .str.strip()
        .replace("", "Não informado")
        .value_counts()
        .rename_axis(
            "tipo_vistoria"
        )
        .reset_index(
            name="quantidade"
        )
    )

    total = int(
        result["quantidade"].sum()
    )

    result["percentual"] = (
        result["quantidade"]
        / total
        * 100
        if total
        else 0
    )

    result["percentual"] = (
        result["percentual"]
        .round(2)
    )

    return result


# ============================================================
# FATURAMENTO POR ECV
# ============================================================

def get_ecv_revenue(df) -> pd.DataFrame:
    """
    Calcula faturamento por ECV.
    """

    df = _copy_df(df)

    columns = [
        "ecv",
        "faturamento",
        "vistorias",
        "ticket_medio",
    ]

    if df.empty:
        return _empty_dataframe(columns)

    _ensure_columns(
        df,
        [
            "ecv",
            "valor",
        ],
    )

    work = df.copy()

    work["valor_num"] = _numeric(
        work["valor"]
    )

    result = (
        work.groupby(
            "ecv",
            dropna=False,
        )
        .agg(
            faturamento=(
                "valor_num",
                "sum",
            ),
            vistorias=(
                "ecv",
                "count",
            ),
        )
        .reset_index()
    )

    result["faturamento"] = (
        result["faturamento"]
        .fillna(0)
        .round(2)
    )

    result["ticket_medio"] = (
        result["faturamento"]
        /
        result["vistorias"].replace(
            0,
            pd.NA,
        )
    ).fillna(0)

    result["ticket_medio"] = (
        result["ticket_medio"]
        .round(2)
    )

    return (
        result
        .sort_values(
            "faturamento",
            ascending=False,
        )
        .reset_index(drop=True)
    )


# ============================================================
# PRODUTIVIDADE
# ============================================================

def get_productivity(df) -> pd.DataFrame:
    """
    Calcula produtividade.

    Prioridade:
        vistoriador

    Fallback:
        ecv
    """

    df = _copy_df(df)

    columns = [
        "responsavel",
        "vistorias",
        "tempo_medio",
        "faturamento",
        "ticket_medio",
    ]

    if df.empty:
        return _empty_dataframe(columns)

    group_col = (
        "vistoriador"
        if "vistoriador" in df.columns
        else "ecv"
    )

    _ensure_columns(
        df,
        [
            group_col,
            "tempo_minutos",
            "valor",
        ],
    )

    work = df.copy()

    work["tempo_num"] = _numeric(
        work["tempo_minutos"]
    )

    work["valor_num"] = _numeric(
        work["valor"]
    )

    result = (
        work.groupby(
            group_col,
            dropna=False,
        )
        .agg(
            vistorias=(
                group_col,
                "count",
            ),
            tempo_medio=(
                "tempo_num",
                "mean",
            ),
            faturamento=(
                "valor_num",
                "sum",
            ),
        )
        .reset_index()
        .rename(
            columns={
                group_col: "responsavel",
            }
        )
    )

    result["tempo_medio"] = (
        result["tempo_medio"]
        .fillna(0)
        .round(2)
    )

    result["faturamento"] = (
        result["faturamento"]
        .fillna(0)
        .round(2)
    )

    result["ticket_medio"] = (
        result["faturamento"]
        /
        result["vistorias"].replace(
            0,
            pd.NA,
        )
    ).fillna(0)

    result["ticket_medio"] = (
        result["ticket_medio"]
        .round(2)
    )

    return (
        result
        .sort_values(
            "vistorias",
            ascending=False,
        )
        .reset_index(drop=True)
    )


# ============================================================
# OUTLIERS DE TEMPO
# ============================================================

def get_time_outliers(
    df,
    z_limit: float = 2.5,
) -> pd.DataFrame:
    """
    Identifica vistorias com tempo operacional
    significativamente acima ou abaixo da média.

    Utiliza desvio padrão.

    Retorna os registros identificados.
    """

    df = _copy_df(df)

    if (
        df.empty
        or "tempo_minutos" not in df.columns
    ):
        return pd.DataFrame()

    work = df.copy()

    work["tempo_num"] = _numeric(
        work["tempo_minutos"]
    )

    valid = work[
        work["tempo_num"].notna()
    ].copy()

    if len(valid) < 3:
        return pd.DataFrame()

    mean = valid[
        "tempo_num"
    ].mean()

    std = valid[
        "tempo_num"
    ].std()

    if not std or pd.isna(std):
        return pd.DataFrame()

    valid["z_score_tempo"] = (
        valid["tempo_num"]
        - mean
    ) / std

    result = valid[
        valid["z_score_tempo"].abs()
        >= z_limit
    ].copy()

    result["desvio_tempo"] = (
        result["tempo_num"]
        - mean
    ).round(2)

    return result.sort_values(
        "z_score_tempo",
        ascending=False,
    )


# ============================================================
# QUALIDADE DOS DADOS
# ============================================================

def _normalize_plate(value):

    if pd.isna(value):
        return ""

    return re.sub(
        r"[^A-Z0-9]",
        "",
        str(value).upper(),
    )


def _valid_plate(value):

    plate = _normalize_plate(
        value
    )

    if not plate:
        return False

    old_pattern = (
        r"^[A-Z]{3}\d{4}$"
    )

    mercosur_pattern = (
        r"^[A-Z]{3}\d[A-Z]\d{2}$"
    )

    return bool(
        re.match(
            old_pattern,
            plate,
        )
        or re.match(
            mercosur_pattern,
            plate,
        )
    )


def get_quality_report(
    df,
) -> Dict[str, Any]:
    """
    Avalia qualidade básica da base.

    Indicadores:
        duplicados
        nulos
        placas inválidas
        datas inválidas
        valores inválidos
        score
    """

    df = _copy_df(df)

    total = int(len(df))

    if total == 0:

        return {
            "total": 0,
            "duplicados": 0,
            "nulos": 0,
            "placas_invalidas": 0,
            "datas_invalidas": 0,
            "valores_invalidos": 0,
            "score": 100.0,
            "status": "Excelente",
            "mensagens": [
                "Nenhum registro disponível para análise."
            ],
        }

    _ensure_columns(
        df,
        [
            "placa",
            "data_vistoria",
            "ecv",
            "resultado",
            "valor",
        ],
    )

    # --------------------------------------------------------
    # DUPLICIDADES
    # --------------------------------------------------------

    duplicate_subset = [
        col
        for col in [
            "placa",
            "data_vistoria",
            "ecv",
        ]
        if col in df.columns
    ]

    duplicados = 0

    if duplicate_subset:

        duplicados = int(
            df.duplicated(
                subset=duplicate_subset,
                keep=False,
            ).sum()
        )

    # --------------------------------------------------------
    # NULOS
    # --------------------------------------------------------

    nulos = int(
        df.isna()
        .sum()
        .sum()
    )

    # Strings vazias

    text_nulls = 0

    for col in df.select_dtypes(
        include=[
            "object",
            "string",
        ]
    ).columns:

        text_nulls += int(
            df[col]
            .fillna("")
            .astype(str)
            .str.strip()
            .eq("")
            .sum()
        )

    nulos += text_nulls

    # --------------------------------------------------------
    # PLACAS INVÁLIDAS
    # --------------------------------------------------------

    placas_invalidas = int(
        (
            ~df["placa"]
            .apply(_valid_plate)
        ).sum()
    )

    # --------------------------------------------------------
    # DATAS INVÁLIDAS
    # --------------------------------------------------------

    dates = pd.to_datetime(
        df["data_vistoria"],
        errors="coerce",
    )

    datas_invalidas = int(
        dates.isna().sum()
    )

    # --------------------------------------------------------
    # VALORES INVÁLIDOS
    # --------------------------------------------------------

    valores = _numeric(
        df["valor"]
    )

    valores_invalidos = int(
        valores.isna().sum()
    )

    # --------------------------------------------------------
    # TAXAS
    # --------------------------------------------------------

    duplicate_rate = (
        duplicados / total
    )

    null_rate = (
        nulos
        /
        max(
            total
            * max(
                len(df.columns),
                1,
            ),
            1,
        )
    )

    invalid_plate_rate = (
        placas_invalidas / total
    )

    invalid_date_rate = (
        datas_invalidas / total
    )

    invalid_value_rate = (
        valores_invalidos / total
    )

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    penalty = (
        duplicate_rate * 25
        + null_rate * 25
        + invalid_plate_rate * 20
        + invalid_date_rate * 15
        + invalid_value_rate * 15
    )

    score = max(
        0.0,
        min(
            100.0,
            100 - penalty * 100,
        ),
    )

    score = round(
        score,
        2,
    )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    if score >= 95:

        status = "Excelente"

    elif score >= 85:

        status = "Boa"

    elif score >= 70:

        status = "Atenção"

    else:

        status = "Crítica"

    # --------------------------------------------------------
    # MENSAGENS
    # --------------------------------------------------------

    mensagens = [
        (
            f"🔎 Foram analisados "
            f"{_format_number(total)} registros."
        ),
        (
            f"🔁 Duplicidades potenciais: "
            f"{_format_number(duplicados)}."
        ),
        (
            f"⬜ Campos vazios: "
            f"{_format_number(nulos)}."
        ),
        (
            f"🚘 Placas fora do padrão: "
            f"{_format_number(placas_invalidas)}."
        ),
        (
            f"📅 Datas inválidas ou ausentes: "
            f"{_format_number(datas_invalidas)}."
        ),
        (
            f"💰 Valores inválidos ou ausentes: "
            f"{_format_number(valores_invalidos)}."
        ),
        (
            f"📊 Score de qualidade: "
            f"{score:.1f}% ({status})."
        ),
    ]

    if duplicados:

        mensagens.append(
            "⚠️ Existem registros potencialmente duplicados."
        )

    if placas_invalidas:

        mensagens.append(
            "⚠️ Existem placas fora do padrão esperado."
        )

    if datas_invalidas:

        mensagens.append(
            "⚠️ Existem datas inválidas ou não informadas."
        )

    if valores_invalidos:

        mensagens.append(
            "⚠️ Existem valores financeiros inválidos ou ausentes."
        )

    if nulos:

        mensagens.append(
            "⚠️ Existem campos vazios na base."
        )

    if (
        not duplicados
        and not placas_invalidas
        and not datas_invalidas
        and not valores_invalidos
        and not nulos
    ):

        mensagens.append(
            "✅ Nenhuma inconsistência básica foi identificada."
        )

    return {
        "total": total,
        "duplicados": duplicados,
        "nulos": nulos,
        "placas_invalidas": placas_invalidas,
        "datas_invalidas": datas_invalidas,
        "valores_invalidos": valores_invalidos,
        "score": score,
        "status": status,
        "mensagens": mensagens,
    }


# ============================================================
# ANOMALIAS OPERACIONAIS
# ============================================================

def get_operational_anomalies(
    df,
) -> Dict[str, Any]:
    """
    Identifica sinais básicos de anomalia operacional.
    """

    df = _copy_df(df)

    if df.empty:

        return {
            "total_anomalias": 0,
            "alto_tempo": 0,
            "baixa_aprovacao_ecv": 0,
            "resultado_desconhecido": 0,
            "mensagens": [],
        }

    anomalies = []

    # --------------------------------------------------------
    # TEMPO
    # --------------------------------------------------------

    high_time = 0

    if "tempo_minutos" in df.columns:

        tempo = _numeric(
            df["tempo_minutos"]
        )

        valid = tempo.dropna()

        if len(valid) >= 3:

            mean = valid.mean()
            std = valid.std()

            if std and not pd.isna(std):

                high_time = int(
                    (
                        tempo
                        > mean + 2 * std
                    ).sum()
                )

    if high_time:

        anomalies.append(
            (
                "⏱️ "
                f"{_format_number(high_time)} "
                "vistorias apresentam tempo acima "
                "do padrão estatístico."
            )
        )

    # --------------------------------------------------------
    # APROVAÇÃO POR ECV
    # --------------------------------------------------------

    performance = get_ecv_performance(
        df
    )

    baixa_aprovacao = 0

    if not performance.empty:

        media = performance[
            "taxa_aprovacao"
        ].mean()

        baixa_aprovacao = int(
            (
                performance[
                    "taxa_aprovacao"
                ]
                < media - 10
            ).sum()
        )

    if baixa_aprovacao:

        anomalies.append(
            (
                "🏢 "
                f"{_format_number(baixa_aprovacao)} "
                "ECVs estão mais de 10 pontos "
                "percentuais abaixo da média."
            )
        )

    # --------------------------------------------------------
    # RESULTADOS DESCONHECIDOS
    # --------------------------------------------------------

    resultado_desconhecido = 0

    if "resultado" in df.columns:

        result = (
            df["resultado"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
        )

        resultado_desconhecido = int(
            ~result.isin(
                [
                    "aprovado",
                    "reprovado",
                ]
            ).sum()
        )

    if resultado_desconhecido:

        anomalies.append(
            (
                "📋 "
                f"{_format_number(resultado_desconhecido)} "
                "registros possuem resultado não "
                "classificado."
            )
        )

    return {
        "total_anomalias": (
            high_time
            + baixa_aprovacao
            + resultado_desconhecido
        ),
        "alto_tempo": high_time,
        "baixa_aprovacao_ecv": baixa_aprovacao,
        "resultado_desconhecido": (
            resultado_desconhecido
        ),
        "mensagens": anomalies,
    }


# ============================================================
# RESUMO EXECUTIVO
# ============================================================

def get_executive_summary(
    df,
) -> Dict[str, Any]:
    """
    Cria um resumo completo para Dashboard e IA.
    """

    kpis = get_kpis(df)

    perf = get_ecv_performance(
        df
    )

    quality = get_quality_report(
        df
    )

    anomalies = get_operational_anomalies(
        df
    )

    daily = get_daily_series(
        df
    )

    summary = {
        "kpis": kpis,
        "quality": quality,
        "anomalies": anomalies,
        "ecvs": int(
            len(perf)
        ),
        "melhor_ecv": None,
        "melhor_aprovacao": 0.0,
        "pior_ecv": None,
        "pior_aprovacao": 0.0,
        "media_aprovacao_ecvs": 0.0,
        "melhor_faturamento_ecv": None,
        "volume_medio_diario": 0.0,
        "dias_analisados": int(
            len(daily)
        ),
    }

    if not perf.empty:

        media = _safe_float(
            perf[
                "taxa_aprovacao"
            ].mean()
        )

        summary[
            "media_aprovacao_ecvs"
        ] = round(
            media,
            2,
        )

        best = perf.iloc[0]

        worst = perf.iloc[-1]

        revenue = (
            perf
            .sort_values(
                "faturamento",
                ascending=False,
            )
            .iloc[0]
        )

        summary.update(
            {
                "melhor_ecv": str(
                    best["ecv"]
                ),
                "melhor_aprovacao": _safe_float(
                    best[
                        "taxa_aprovacao"
                    ]
                ),
                "pior_ecv": str(
                    worst["ecv"]
                ),
                "pior_aprovacao": _safe_float(
                    worst[
                        "taxa_aprovacao"
                    ]
                ),
                "melhor_faturamento_ecv": str(
                    revenue["ecv"]
                ),
            }
        )

    if not daily.empty:

        summary[
            "volume_medio_diario"
        ] = round(
            _safe_float(
                daily[
                    "vistorias"
                ].mean()
            ),
            2,
        )

    return summary


# ============================================================
# PAYLOAD PARA IA / LLM
# ============================================================

def get_ai_context(
    df,
) -> Dict[str, Any]:
    """
    Monta contexto estruturado para o LLM.

    A IA recebe indicadores calculados,
    em vez de depender apenas de linhas brutas.
    """

    df = _copy_df(df)

    executive = get_executive_summary(
        df
    )

    performance = get_ecv_performance(
        df
    )

    results = get_result_distribution(
        df
    )

    types = get_type_distribution(
        df
    )

    daily = get_daily_trend(
        df
    )

    below_average = get_ecvs_below_average(
        df
    )

    context = {
        "executive": executive,
        "resultados": results.to_dict(
            orient="records"
        ),
        "tipos_vistoria": types.to_dict(
            orient="records"
        ),
        "performance_ecv": performance.head(
            20
        ).to_dict(
            orient="records"
        ),
        "ecvs_abaixo_media": below_average.head(
            20
        ).to_dict(
            orient="records"
        ),
        "tendencia_diaria": daily.tail(
            30
        ).to_dict(
            orient="records"
        ),
    }

    return context


# ============================================================
# HEALTH CHECK DOS DADOS
# ============================================================

def get_analytics_health(
    df,
) -> Dict[str, Any]:
    """
    Retorna status técnico da camada analítica.
    """

    df = _copy_df(df)

    if df.empty:

        return {
            "status": "empty",
            "registros": 0,
            "colunas": 0,
            "kpis_ok": False,
            "performance_ok": False,
            "quality_ok": True,
        }

    try:

        kpis = get_kpis(
            df
        )

        perf = get_ecv_performance(
            df
        )

        quality = get_quality_report(
            df
        )

        return {
            "status": "healthy",
            "registros": int(
                len(df)
            ),
            "colunas": int(
                len(df.columns)
            ),
            "kpis_ok": bool(
                isinstance(
                    kpis,
                    dict,
                )
            ),
            "performance_ok": bool(
                isinstance(
                    perf,
                    pd.DataFrame,
                )
            ),
            "quality_ok": bool(
                isinstance(
                    quality,
                    dict,
                )
            ),
        }

    except Exception as exc:

        return {
            "status": "error",
            "registros": int(
                len(df)
            ),
            "colunas": int(
                len(df.columns)
            ),
            "kpis_ok": False,
            "performance_ok": False,
            "quality_ok": False,
            "error": str(exc),
        }
```
