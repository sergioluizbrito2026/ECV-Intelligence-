"""
ECV Intelligence V3
services/analytics.py

Camada de indicadores e análise operacional.

Objetivos:
- KPIs executivos
- séries temporais
- desempenho por ECV
- qualidade dos dados
- produtividade
- faturamento
- resumo executivo para IA
"""

import re
import pandas as pd


# ============================================================
# UTILITÁRIOS
# ============================================================

def _copy_df(df):
    if df is None:
        return pd.DataFrame()
    return df.copy()


def _numeric(series):
    return pd.to_numeric(series, errors="coerce")


def _ensure_columns(df, columns):
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
    return df


# ============================================================
# KPIs
# ============================================================

def get_kpis(df):
    """
    Calcula os principais indicadores operacionais.

    Retorno:
        total
        aprovadas
        reprovadas
        taxa_aprovacao
        taxa_reprovacao
        tempo_medio
        faturamento
    """

    df = _copy_df(df)

    if df.empty:
        return {
            "total": 0,
            "aprovadas": 0,
            "reprovadas": 0,
            "taxa_aprovacao": 0.0,
            "taxa_reprovacao": 0.0,
            "tempo_medio": 0.0,
            "faturamento": 0.0,
        }

    _ensure_columns(
        df,
        [
            "resultado",
            "tempo_minutos",
            "valor",
        ],
    )

    resultado = (
        df["resultado"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    aprovadas = int(
        (resultado == "aprovado").sum()
    )

    reprovadas = int(
        (resultado == "reprovado").sum()
    )

    total = int(len(df))

    tempo = _numeric(
        df["tempo_minutos"]
    )

    valor = _numeric(
        df["valor"]
    )

    return {
        "total": total,
        "aprovadas": aprovadas,
        "reprovadas": reprovadas,
        "taxa_aprovacao": round(
            aprovadas / total * 100,
            2
        ) if total else 0.0,
        "taxa_reprovacao": round(
            reprovadas / total * 100,
            2
        ) if total else 0.0,
        "tempo_medio": round(
            float(tempo.mean()),
            2
        ) if tempo.notna().any() else 0.0,
        "faturamento": round(
            float(valor.sum()),
            2
        ) if valor.notna().any() else 0.0,
    }


# ============================================================
# SÉRIE DIÁRIA
# ============================================================

def get_daily_series(df):
    """
    Agrupa as vistorias por dia.

    Retorno:
        data
        vistorias
    """

    df = _copy_df(df)

    if df.empty:
        return pd.DataFrame(
            columns=[
                "data",
                "vistorias",
            ]
        )

    _ensure_columns(
        df,
        ["data_vistoria"]
    )

    dates = pd.to_datetime(
        df["data_vistoria"],
        errors="coerce"
    )

    result = (
        pd.DataFrame(
            {
                "data": dates.dt.date
            }
        )
        .dropna(subset=["data"])
        .groupby("data")
        .size()
        .reset_index(
            name="vistorias"
        )
    )

    return (
        result
        .sort_values("data")
        .reset_index(drop=True)
    )


# ============================================================
# DESEMPENHO POR ECV
# ============================================================

def get_ecv_performance(df):
    """
    Calcula desempenho operacional por ECV.

    Retorno:
        ecv
        total
        aprovadas
        tempo_medio
        taxa_aprovacao
    """

    df = _copy_df(df)

    if df.empty:
        return pd.DataFrame(
            columns=[
                "ecv",
                "total",
                "aprovadas",
                "tempo_medio",
                "taxa_aprovacao",
            ]
        )

    _ensure_columns(
        df,
        [
            "ecv",
            "id",
            "resultado",
            "tempo_minutos",
        ],
    )

    df["resultado_norm"] = (
        df["resultado"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    df["aprovado"] = (
        df["resultado_norm"]
        == "aprovado"
    )

    df["tempo_num"] = _numeric(
        df["tempo_minutos"]
    )

    result = (
        df.groupby(
            "ecv",
            dropna=False
        )
        .agg(
            total=("id", "count"),
            aprovadas=("aprovado", "sum"),
            tempo_medio=("tempo_num", "mean"),
        )
        .reset_index()
    )

    result["taxa_aprovacao"] = (
        result["aprovadas"]
        /
        result["total"].replace(
            0,
            pd.NA
        )
        * 100
    )

    result["taxa_aprovacao"] = (
        result["taxa_aprovacao"]
        .fillna(0)
        .round(2)
    )

    result["tempo_medio"] = (
        result["tempo_medio"]
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
# DISTRIBUIÇÃO DE RESULTADOS
# ============================================================

def get_result_distribution(df):

    df = _copy_df(df)

    if (
        df.empty
        or "resultado" not in df.columns
    ):
        return pd.DataFrame(
            columns=[
                "resultado",
                "quantidade",
                "percentual",
            ]
        )

    result = (
        df["resultado"]
        .fillna("Não informado")
        .astype(str)
        .value_counts()
        .rename_axis("resultado")
        .reset_index(
            name="quantidade"
        )
    )

    total = result["quantidade"].sum()

    result["percentual"] = (
        result["quantidade"]
        / total
        * 100
        if total
        else 0
    )

    return result


# ============================================================
# TIPOS DE VISTORIA
# ============================================================

def get_type_distribution(df):

    df = _copy_df(df)

    if (
        df.empty
        or "tipo_vistoria" not in df.columns
    ):
        return pd.DataFrame(
            columns=[
                "tipo_vistoria",
                "quantidade",
                "percentual",
            ]
        )

    result = (
        df["tipo_vistoria"]
        .fillna("Não informado")
        .astype(str)
        .value_counts()
        .rename_axis("tipo_vistoria")
        .reset_index(
            name="quantidade"
        )
    )

    total = result["quantidade"].sum()

    result["percentual"] = (
        result["quantidade"]
        / total
        * 100
        if total
        else 0
    )

    return result


# ============================================================
# FATURAMENTO POR ECV
# ============================================================

def get_ecv_revenue(df):

    df = _copy_df(df)

    if df.empty:
        return pd.DataFrame(
            columns=[
                "ecv",
                "faturamento",
                "vistorias",
                "ticket_medio",
            ]
        )

    _ensure_columns(
        df,
        [
            "ecv",
            "valor",
        ],
    )

    df["valor_num"] = _numeric(
        df["valor"]
    )

    result = (
        df.groupby(
            "ecv",
            dropna=False
        )
        .agg(
            faturamento=(
                "valor_num",
                "sum"
            ),
            vistorias=(
                "valor_num",
                "count"
            ),
        )
        .reset_index()
    )

    result["ticket_medio"] = (
        result["faturamento"]
        /
        result["vistorias"].replace(
            0,
            pd.NA
        )
    ).fillna(0)

    return (
        result
        .sort_values(
            "faturamento",
            ascending=False
        )
        .reset_index(drop=True)
    )


# ============================================================
# PRODUTIVIDADE
# ============================================================

def get_productivity(df):

    df = _copy_df(df)

    if df.empty:
        return pd.DataFrame(
            columns=[
                "responsavel",
                "vistorias",
                "tempo_medio",
            ]
        )

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
        ],
    )

    df["tempo_num"] = _numeric(
        df["tempo_minutos"]
    )

    result = (
        df.groupby(
            group_col,
            dropna=False
        )
        .agg(
            vistorias=(
                "tempo_num",
                "count"
            ),
            tempo_medio=(
                "tempo_num",
                "mean"
            ),
        )
        .reset_index()
        .rename(
            columns={
                group_col: "responsavel"
            }
        )
    )

    result["tempo_medio"] = (
        result["tempo_medio"]
        .fillna(0)
        .round(2)
    )

    return (
        result
        .sort_values(
            "vistorias",
            ascending=False
        )
        .reset_index(drop=True)
    )


# ============================================================
# VALIDAÇÃO DE PLACAS
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

    # Modelo antigo
    old_pattern = (
        r"^[A-Z]{3}\d{4}$"
    )

    # Mercosul
    mercosur_pattern = (
        r"^[A-Z]{3}\d[A-Z]\d{2}$"
    )

    return bool(
        re.match(
            old_pattern,
            plate
        )
        or
        re.match(
            mercosur_pattern,
            plate
        )
    )


# ============================================================
# QUALIDADE DOS DADOS
# ============================================================

def get_quality_report(df):

    df = _copy_df(df)

    total = int(len(df))

    if total == 0:

        return {
            "total": 0,
            "duplicados": 0,
            "nulos": 0,
            "placas_invalidas": 0,
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

    if duplicate_subset:

        duplicados = int(
            df.duplicated(
                subset=duplicate_subset,
                keep=False,
            ).sum()
        )

    else:

        duplicados = 0

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
    # SCORE
    # --------------------------------------------------------

    duplicate_rate = (
        duplicados / total
    )

    null_rate = (
        nulos
        /
        max(
            total * max(
                len(df.columns),
                1
            ),
            1,
        )
    )

    invalid_rate = (
        placas_invalidas / total
    )

    penalty = (
        duplicate_rate * 35
        +
        null_rate * 35
        +
        invalid_rate * 30
    )

    score = max(
        0.0,
        min(
            100.0,
            100 - penalty * 100
        ),
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
        f"🔎 Foram analisados {total:,} registros.".replace(
            ",",
            ".",
        ),

        f"🔁 Duplicidades potenciais: {duplicados}.",

        f"⬜ Campos vazios: {nulos}.",

        f"🚘 Placas fora do padrão esperado: {placas_invalidas}.",

        f"📊 Score calculado: {score:.1f}% ({status}).",
    ]

    if duplicados:

        mensagens.append(
            "⚠️ Existem registros potencialmente "
            "duplicados que devem ser revisados."
        )

    if placas_invalidas:

        mensagens.append(
            "⚠️ Existem placas que não seguem "
            "o padrão esperado."
        )

    if nulos:

        mensagens.append(
            "⚠️ Existem campos vazios na base."
        )

    if (
        not duplicados
        and not placas_invalidas
        and not nulos
    ):

        mensagens.append(
            "✅ Nenhuma inconsistência básica "
            "foi identificada."
        )

    mensagens.append(
        "💡 Na versão comercial poderão ser "
        "adicionadas regras para validar datas, "
        "valores, integridade referencial e "
        "consistência entre sistemas."
    )

    return {
        "total": total,
        "duplicados": duplicados,
        "nulos": nulos,
        "placas_invalidas": placas_invalidas,
        "score": round(
            score,
            2
        ),
        "status": status,
        "mensagens": mensagens,
    }


# ============================================================
# RESUMO EXECUTIVO
# ============================================================

def get_executive_summary(df):

    kpis = get_kpis(df)

    perf = get_ecv_performance(
        df
    )

    quality = get_quality_report(
        df
    )

    summary = {
        "kpis": kpis,
        "quality": quality,
        "ecvs": int(
            len(perf)
        ),
        "melhor_ecv": None,
        "melhor_aprovacao": 0.0,
        "pior_ecv": None,
        "pior_aprovacao": 0.0,
    }

    if not perf.empty:

        best = perf.iloc[0]

        worst = perf.iloc[-1]

        summary.update(
            {
                "melhor_ecv": best["ecv"],
                "melhor_aprovacao": float(
                    best["taxa_aprovacao"]
                ),
                "pior_ecv": worst["ecv"],
                "pior_aprovacao": float(
                    worst["taxa_aprovacao"]
                ),
            }
        )

    return summary
