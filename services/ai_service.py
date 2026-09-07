
"""
ECV Intelligence V4
services/ai_service.py

Motor de Inteligência Artificial do ECV Intelligence.

Responsabilidades:
- integração com Google Gemini;
- análise executiva dos KPIs;
- Copilot de dados;
- análise estatística da operação;
- ranking de ECVs;
- análise de resultados;
- análise de faturamento;
- análise de tempo operacional;
- análise por cidade e tipo de vistoria;
- detecção básica de anomalias;
- recomendações gerenciais;
- fallback determinístico;
- proteção contra respostas inventadas;
- controle de contexto;
- tratamento robusto de erros.

Compatibilidade:
    app.py V3/V4
    services/analytics.py
"""

import json
import os
import re
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from google import genai


# ============================================================
# CONFIGURAÇÃO
# ============================================================

DEFAULT_MODEL = "gemini-2.5-flash"

MAX_ROWS_CONTEXT = 80
MAX_TEXT_LENGTH = 12000
MAX_PERFORMANCE_ROWS = 50
MAX_RANKING_ROWS = 20

DEFAULT_TEMPO_ALERTA = 60.0
DEFAULT_APROVACAO_ALERTA = 75.0


# ============================================================
# CLIENT GEMINI
# ============================================================

def _get_api_key() -> Optional[str]:
    """
    Obtém a chave da API Gemini.

    Prioridade:
    1. Streamlit Secrets
    2. variável de ambiente
    """

    try:

        if (
            hasattr(st, "secrets")
            and "GEMINI_API_KEY" in st.secrets
        ):

            key = st.secrets["GEMINI_API_KEY"]

            if key:

                return str(key).strip()

    except Exception:
        pass

    key = os.getenv("GEMINI_API_KEY")

    if key:

        return key.strip()

    return None


def _get_model() -> str:
    """
    Retorna o modelo configurado.
    """

    model = os.getenv(
        "GEMINI_MODEL",
        DEFAULT_MODEL,
    )

    model = str(model).strip()

    return model or DEFAULT_MODEL


def _get_gemini_client():
    """
    Cria cliente Gemini.

    Retorna:
        Cliente Gemini ou None.
    """

    api_key = _get_api_key()

    if not api_key:

        return None

    try:

        return genai.Client(
            api_key=api_key
        )

    except Exception:

        return None


# ============================================================
# UTILITÁRIOS
# ============================================================

def _safe_float(
    value,
    default=0.0,
):
    """
    Conversão numérica segura.
    """

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


def _format_number(value):
    """
    Formata número no padrão brasileiro.
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


def _format_money(value):
    """
    Formata moeda brasileira.
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


def _clean_text(text):
    """
    Limita tamanho da resposta da LLM.
    """

    if not text:

        return ""

    text = str(text).strip()

    if len(text) > MAX_TEXT_LENGTH:

        return (
            text[:MAX_TEXT_LENGTH]
            .rstrip()
            + "..."
        )

    return text


def _normalize_question(question):
    """
    Normaliza pergunta do usuário.
    """

    return re.sub(
        r"\s+",
        " ",
        str(question or "")
        .strip()
        .lower(),
    )


def _safe_json(data):
    """
    Converte objetos para JSON de forma segura.
    """

    try:

        return json.dumps(
            data,
            ensure_ascii=False,
            default=str,
        )

    except Exception:

        return "{}"


# ============================================================
# PREPARAÇÃO DA BASE
# ============================================================

def _prepare_dataframe(df):
    """
    Cria uma cópia segura da base.

    Não altera o DataFrame original.
    """

    if df is None:

        return pd.DataFrame()

    if not isinstance(
        df,
        pd.DataFrame,
    ):

        try:

            df = pd.DataFrame(df)

        except Exception:

            return pd.DataFrame()

    if df.empty:

        return pd.DataFrame()

    work = df.copy()

    return work


# ============================================================
# KPIs
# ============================================================

def _calculate_kpis(df):
    """
    Calcula indicadores diretamente sobre a base.
    """

    work = _prepare_dataframe(df)

    if work.empty:

        return {
            "total": 0,
            "aprovadas": 0,
            "reprovadas": 0,
            "taxa_aprovacao": 0.0,
            "taxa_reprovacao": 0.0,
            "tempo_medio": 0.0,
            "faturamento": 0.0,
            "ecvs": 0,
            "cidades": 0,
        }

    total = len(work)

    aprovadas = 0
    reprovadas = 0

    if "resultado" in work.columns:

        resultado = (
            work["resultado"]
            .fillna("")
            .astype(str)
            .str.lower()
            .str.strip()
        )

        aprovadas = int(
            resultado
            .str.contains(
                "aprov",
                na=False,
            )
            .sum()
        )

        reprovadas = int(
            resultado
            .str.contains(
                "reprov",
                na=False,
            )
            .sum()
        )

    taxa_aprovacao = (
        aprovadas
        / total
        * 100
        if total
        else 0.0
    )

    taxa_reprovacao = (
        reprovadas
        / total
        * 100
        if total
        else 0.0
    )

    tempo_medio = 0.0

    if "tempo_minutos" in work.columns:

        tempo = pd.to_numeric(
            work["tempo_minutos"],
            errors="coerce",
        )

        if tempo.notna().any():

            tempo_medio = _safe_float(
                tempo.mean()
            )

    faturamento = 0.0

    if "valor" in work.columns:

        valor = pd.to_numeric(
            work["valor"],
            errors="coerce",
        )

        faturamento = _safe_float(
            valor.sum()
        )

    ecvs = 0

    if "ecv" in work.columns:

        ecvs = int(
            work["ecv"]
            .dropna()
            .astype(str)
            .nunique()
        )

    cidades = 0

    if "cidade" in work.columns:

        cidades = int(
            work["cidade"]
            .dropna()
            .astype(str)
            .nunique()
        )

    return {
        "total": total,
        "aprovadas": aprovadas,
        "reprovadas": reprovadas,
        "taxa_aprovacao": round(
            taxa_aprovacao,
            2,
        ),
        "taxa_reprovacao": round(
            taxa_reprovacao,
            2,
        ),
        "tempo_medio": round(
            tempo_medio,
            2,
        ),
        "faturamento": round(
            faturamento,
            2,
        ),
        "ecvs": ecvs,
        "cidades": cidades,
    }


# ============================================================
# RANKING ECV
# ============================================================

def _calculate_ecv_performance(df):
    """
    Calcula desempenho por ECV.
    """

    work = _prepare_dataframe(df)

    if work.empty:

        return pd.DataFrame()

    required = {
        "ecv",
        "resultado",
    }

    if not required.issubset(
        set(work.columns)
    ):

        return pd.DataFrame()

    work["resultado_normalizado"] = (
        work["resultado"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.strip()
    )

    grouped = []

    for ecv, group in work.groupby(
        "ecv",
        dropna=True,
    ):

        total = len(group)

        aprovadas = int(
            group["resultado_normalizado"]
            .str.contains(
                "aprov",
                na=False,
            )
            .sum()
        )

        reprovadas = int(
            group["resultado_normalizado"]
            .str.contains(
                "reprov",
                na=False,
            )
            .sum()
        )

        taxa = (
            aprovadas
            / total
            * 100
            if total
            else 0
        )

        tempo_medio = 0.0

        if "tempo_minutos" in group.columns:

            tempo = pd.to_numeric(
                group["tempo_minutos"],
                errors="coerce",
            )

            if tempo.notna().any():

                tempo_medio = _safe_float(
                    tempo.mean()
                )

        faturamento = 0.0

        if "valor" in group.columns:

            valor = pd.to_numeric(
                group["valor"],
                errors="coerce",
            )

            faturamento = _safe_float(
                valor.sum()
            )

        grouped.append(
            {
                "ecv": str(ecv),
                "vistorias": total,
                "aprovadas": aprovadas,
                "reprovadas": reprovadas,
                "taxa_aprovacao": round(
                    taxa,
                    2,
                ),
                "tempo_medio": round(
                    tempo_medio,
                    2,
                ),
                "faturamento": round(
                    faturamento,
                    2,
                ),
            }
        )

    result = pd.DataFrame(
        grouped
    )

    if result.empty:

        return result

    return result.sort_values(
        "taxa_aprovacao",
        ascending=False,
    ).reset_index(
        drop=True
    )


# ============================================================
# DISTRIBUIÇÕES
# ============================================================

def _value_distribution(
    df,
    column,
    limit=20,
):
    """
    Retorna distribuição de uma coluna.
    """

    if (
        df.empty
        or column not in df.columns
    ):

        return []

    values = (
        df[column]
        .fillna("Não informado")
        .astype(str)
        .value_counts()
        .head(limit)
    )

    return [
        {
            "nome": str(index),
            "quantidade": int(value),
        }
        for index, value in values.items()
    ]


# ============================================================
# ANOMALIAS
# ============================================================

def _detect_anomalies(df):
    """
    Detecta sinais simples de anomalia operacional.

    Não utiliza IA para cálculo.
    """

    work = _prepare_dataframe(df)

    if work.empty:

        return []

    anomalies = []

    # --------------------------------------------------------
    # TEMPO
    # --------------------------------------------------------

    if "tempo_minutos" in work.columns:

        tempo = pd.to_numeric(
            work["tempo_minutos"],
            errors="coerce",
        )

        tempo_medio = tempo.mean()

        if (
            pd.notna(tempo_medio)
            and tempo_medio > DEFAULT_TEMPO_ALERTA
        ):

            anomalies.append(
                {
                    "tipo": "tempo_operacional",
                    "severidade": "alta",
                    "indicador": "tempo_medio",
                    "valor": round(
                        float(tempo_medio),
                        2,
                    ),
                    "mensagem": (
                        "O tempo médio das vistorias "
                        "está acima do limite operacional "
                        f"de {DEFAULT_TEMPO_ALERTA:.0f} minutos."
                    ),
                }
            )

    # --------------------------------------------------------
    # APROVAÇÃO
    # --------------------------------------------------------

    if "resultado" in work.columns:

        resultado = (
            work["resultado"]
            .fillna("")
            .astype(str)
            .str.lower()
        )

        total = len(resultado)

        aprovadas = (
            resultado
            .str.contains(
                "aprov",
                na=False,
            )
            .sum()
        )

        taxa = (
            aprovadas
            / total
            * 100
            if total
            else 0
        )

        if taxa < DEFAULT_APROVACAO_ALERTA:

            anomalies.append(
                {
                    "tipo": "qualidade",
                    "severidade": "alta",
                    "indicador": "taxa_aprovacao",
                    "valor": round(
                        float(taxa),
                        2,
                    ),
                    "mensagem": (
                        "A taxa de aprovação está abaixo "
                        f"do limite de {DEFAULT_APROVACAO_ALERTA:.0f}%."
                    ),
                }
            )

    # --------------------------------------------------------
    # ECVs
    # --------------------------------------------------------

    performance = _calculate_ecv_performance(
        work
    )

    if not performance.empty:

        low_performance = performance[
            performance["taxa_aprovacao"]
            < DEFAULT_APROVACAO_ALERTA
        ]

        for _, row in low_performance.head(5).iterrows():

            anomalies.append(
                {
                    "tipo": "ecv",
                    "severidade": "media",
                    "indicador": "taxa_aprovacao",
                    "ecv": str(row["ecv"]),
                    "valor": float(
                        row["taxa_aprovacao"]
                    ),
                    "mensagem": (
                        f"A ECV {row['ecv']} apresenta "
                        "taxa de aprovação abaixo do "
                        "limite de referência."
                    ),
                }
            )

    return anomalies


# ============================================================
# RESUMO INTELIGENTE DA BASE
# ============================================================

def _build_data_summary(df):
    """
    Gera um resumo matemático completo da operação.

    A LLM recebe indicadores calculados,
    rankings e distribuições.
    """

    work = _prepare_dataframe(df)

    if work.empty:

        return {
            "kpis": _calculate_kpis(work),
            "performance_ecv": [],
            "resultados": [],
            "tipos_vistoria": [],
            "cidades": [],
            "anomalias": [],
        }

    kpis = _calculate_kpis(
        work
    )

    performance = _calculate_ecv_performance(
        work
    )

    performance_records = []

    if not performance.empty:

        performance_records = (
            performance
            .head(MAX_PERFORMANCE_ROWS)
            .to_dict(
                orient="records"
            )
        )

    return {
        "kpis": kpis,
        "performance_ecv": performance_records,
        "resultados": _value_distribution(
            work,
            "resultado",
            10,
        ),
        "tipos_vistoria": _value_distribution(
            work,
            "tipo_vistoria",
            10,
        ),
        "cidades": _value_distribution(
            work,
            "cidade",
            15,
        ),
        "anomalias": _detect_anomalies(
            work
        ),
    }


# ============================================================
# ANÁLISE EXECUTIVA
# ============================================================

def analyze_data(
    kpi,
    perf,
):
    """
    Gera análise executiva.

    Mantém compatibilidade com o app atual.
    """

    client = _get_gemini_client()

    payload = {
        "kpis": kpi or {},
        "performance": [],
    }

    if isinstance(
        perf,
        pd.DataFrame,
    ):

        payload["performance"] = (
            perf
            .head(MAX_PERFORMANCE_ROWS)
            .to_dict(
                orient="records"
            )
        )

    elif isinstance(
        perf,
        list,
    ):

        payload["performance"] = perf

    if client:

        prompt = f"""
Você é o Diretor de Inteligência Operacional
do ECV Intelligence.

Analise exclusivamente os dados fornecidos.

REGRAS:

1. Nunca invente números.
2. Nunca invente nomes de ECV.
3. Não faça previsões sem dados suficientes.
4. Diferencie claramente fatos de interpretações.
5. Utilize somente indicadores fornecidos.
6. Seja objetivo e executivo.
7. Responda em português do Brasil.
8. Não mencione que é um modelo de IA.
9. Não inclua legislação ou informações externas.
10. Se os dados forem insuficientes, informe isso.

Estruture:

### 📊 Visão Geral

Mostre:
- vistorias;
- aprovação;
- reprovação;
- tempo médio;
- faturamento.

### 🏆 Performance

Identifique:
- melhor ECV;
- pior ECV;
- diferença entre elas.

### 🚨 Pontos de Atenção

Identifique indicadores que merecem acompanhamento.

### 🎯 Recomendações

Apresente até 3 ações gerenciais.

DADOS:

{_safe_json(payload)}
"""

        try:

            response = client.models.generate_content(
                model=_get_model(),
                contents=prompt,
            )

            if response:

                text = getattr(
                    response,
                    "text",
                    None,
                )

                if text:

                    return _clean_text(
                        text
                    )

        except Exception:

            pass

    return _local_executive_analysis(
        kpi,
        perf,
    )


# ============================================================
# FALLBACK EXECUTIVO
# ============================================================

def _local_executive_analysis(
    kpi,
    perf,
):
    """
    Análise executiva sem LLM.
    """

    kpi = kpi or {}

    total = _safe_float(
        kpi.get(
            "total",
            0,
        )
    )

    taxa_aprovacao = _safe_float(
        kpi.get(
            "taxa_aprovacao",
            0,
        )
    )

    taxa_reprovacao = _safe_float(
        kpi.get(
            "taxa_reprovacao",
            0,
        )
    )

    tempo_medio = _safe_float(
        kpi.get(
            "tempo_medio",
            0,
        )
    )

    faturamento = _safe_float(
        kpi.get(
            "faturamento",
            0,
        )
    )

    if not isinstance(
        perf,
        pd.DataFrame,
    ) or perf.empty:

        return f"""
### 📊 Visão Geral

Foram analisadas **{_format_number(total)} vistorias**.

- **Taxa de aprovação:** {taxa_aprovacao:.1f}%
- **Taxa de reprovação:** {taxa_reprovacao:.1f}%
- **Tempo médio:** {tempo_medio:.1f} minutos
- **Faturamento:** {_format_money(faturamento)}

### 🔎 Performance

Não existem dados suficientes para gerar um ranking por ECV.

### 🎯 Recomendação

Ampliar a análise por ECV, período e tipo de vistoria.
"""

    required = {
        "ecv",
        "taxa_aprovacao",
    }

    if not required.issubset(
        set(perf.columns)
    ):

        return f"""
### 📊 Visão Geral

Foram analisadas **{_format_number(total)} vistorias**.

- **Taxa de aprovação:** {taxa_aprovacao:.1f}%
- **Taxa de reprovação:** {taxa_reprovacao:.1f}%
- **Tempo médio:** {tempo_medio:.1f} minutos
- **Faturamento:** {_format_money(faturamento)}

### 🎯 Recomendação

Os dados de desempenho por ECV estão incompletos.
"""

    ranking = perf.copy()

    ranking["taxa_aprovacao"] = pd.to_numeric(
        ranking["taxa_aprovacao"],
        errors="coerce",
    ).fillna(0)

    ranking = ranking.sort_values(
        "taxa_aprovacao",
        ascending=False,
    )

    if ranking.empty:

        return (
            "Não existem dados suficientes "
            "para gerar a análise."
        )

    best = ranking.iloc[0]
    worst = ranking.iloc[-1]

    best_rate = _safe_float(
        best["taxa_aprovacao"]
    )

    worst_rate = _safe_float(
        worst["taxa_aprovacao"]
    )

    difference = (
        best_rate
        - worst_rate
    )

    return f"""
### 📊 Visão Geral

Foram analisadas **{_format_number(total)} vistorias**.

- **Taxa de aprovação:** {taxa_aprovacao:.1f}%
- **Taxa de reprovação:** {taxa_reprovacao:.1f}%
- **Tempo médio:** {tempo_medio:.1f} minutos
- **Faturamento:** {_format_money(faturamento)}

### 🏆 Performance

- **Melhor ECV:** {best["ecv"]} — {best_rate:.1f}%.
- **Menor desempenho:** {worst["ecv"]} — {worst_rate:.1f}%.
- **Diferença:** {difference:.1f} pontos percentuais.

### 🎯 Recomendações

1. Avaliar ECVs abaixo da média.
2. Acompanhar tempo operacional.
3. Monitorar a evolução da aprovação.
"""


# ============================================================
# COPILOT
# ============================================================

def ask_data(
    question,
    df,
):
    """
    Copilot de Dados.

    Estratégia:

    1. Valida a pergunta.
    2. Calcula os dados reais.
    3. Tenta responder perguntas determinísticas.
    4. Utiliza Gemini para perguntas analíticas.
    5. Utiliza fallback local.
    """

    question = str(
        question or ""
    ).strip()

    if not question:

        return (
            "Digite uma pergunta para consultar "
            "os dados operacionais."
        )

    work = _prepare_dataframe(
        df
    )

    if work.empty:

        return (
            "Não existem dados disponíveis "
            "para análise."
        )

    normalized = _normalize_question(
        question
    )

    summary = _build_data_summary(
        work
    )

    # ========================================================
    # RESPOSTAS DETERMINÍSTICAS
    # ========================================================

    local_answer = _answer_common_question(
        normalized,
        summary,
    )

    if local_answer:

        return local_answer

    # ========================================================
    # GEMINI
    # ========================================================

    client = _get_gemini_client()

    if client:

        try:

            sample = work.head(
                MAX_ROWS_CONTEXT
            ).copy()

            prompt = f"""
Você é o Copilot de Dados do ECV Intelligence.

Sua função é analisar dados operacionais de ECVs.

REGRA FUNDAMENTAL:

Você só pode responder utilizando os dados fornecidos.

Nunca invente:
- números;
- ECVs;
- cidades;
- resultados;
- tendências;
- causas;
- valores financeiros.

O resumo matemático possui prioridade sobre
a amostra de registros.

Se não houver dados suficientes,
responda claramente:

"Os dados disponíveis não permitem responder
essa pergunta com segurança."

Responda em português do Brasil.

Se possível, estruture:

### Resposta

### Evidências

### Insight

PERGUNTA:

{question}

RESUMO CALCULADO:

{_safe_json(summary)}

AMOSTRA:

{sample.to_string(index=False)}
"""

            response = client.models.generate_content(
                model=_get_model(),
                contents=prompt,
            )

            if response:

                text = getattr(
                    response,
                    "text",
                    None,
                )

                if text:

                    return _clean_text(
                        text
                    )

        except Exception:

            pass

    return _fallback_question_answer(
        normalized,
        summary,
    )


# ============================================================
# PERGUNTAS DETERMINÍSTICAS
# ============================================================

def _answer_common_question(
    question,
    summary,
):
    """
    Responde perguntas que não precisam de LLM.
    """

    kpis = summary["kpis"]

    performance = summary[
        "performance_ecv"
    ]

    # --------------------------------------------------------
    # TOTAL
    # --------------------------------------------------------

    if (
        (
            "quantas" in question
            or "quantos" in question
            or "total" in question
        )
        and "vistoria" in question
    ):

        return (
            f"A base possui "
            f"**{_format_number(kpis['total'])} "
            f"vistorias**."
        )

    # --------------------------------------------------------
    # QUANTIDADE DE ECVs
    # --------------------------------------------------------

    if (
        (
            "quantas" in question
            or "quantos" in question
        )
        and "ecv" in question
    ):

        return (
            f"A base possui "
            f"**{_format_number(kpis['ecvs'])} ECVs**."
        )

    # --------------------------------------------------------
    # FATURAMENTO
    # --------------------------------------------------------

    if (
        "faturamento" in question
        or "receita" in question
    ):

        return (
            f"O faturamento registrado é "
            f"**{_format_money(kpis['faturamento'])}**."
        )

    # --------------------------------------------------------
    # TEMPO MÉDIO
    # --------------------------------------------------------

    if (
        "tempo" in question
        and (
            "médio" in question
            or "medio" in question
        )
    ):

        return (
            f"O tempo médio das vistorias é "
            f"**{kpis['tempo_medio']:.1f} minutos**."
        )

    # --------------------------------------------------------
    # APROVAÇÃO
    # --------------------------------------------------------

    if (
        "taxa de aprovação" in question
        or "taxa aprovação" in question
        or "aprovação" in question
        or "aprovacao" in question
    ):

        return (
            f"A taxa de aprovação da base é "
            f"**{kpis['taxa_aprovacao']:.1f}%**."
        )

    # --------------------------------------------------------
    # REPROVAÇÃO
    # --------------------------------------------------------

    if (
        "reprovação" in question
        or "reprovacao" in question
    ):

        return (
            f"A taxa de reprovação da base é "
            f"**{kpis['taxa_reprovacao']:.1f}%**."
        )

    # --------------------------------------------------------
    # MELHOR ECV
    # --------------------------------------------------------

    if (
        "melhor" in question
        and "ecv" in question
    ):

        if performance:

            row = performance[0]

            return (
                f"🏆 A ECV com maior taxa de aprovação é "
                f"**{row['ecv']}**, com "
                f"**{row['taxa_aprovacao']:.1f}%**."
            )

    # --------------------------------------------------------
    # PIOR ECV
    # --------------------------------------------------------

    if (
        "pior" in question
        and "ecv" in question
    ):

        if performance:

            row = performance[-1]

            return (
                f"⚠️ A ECV com menor taxa de aprovação é "
                f"**{row['ecv']}**, com "
                f"**{row['taxa_aprovacao']:.1f}%**."
            )

    # --------------------------------------------------------
    # MAIS VISTORIAS
    # --------------------------------------------------------

    if (
        "mais" in question
        and "vistoria" in question
        and "ecv" in question
    ):

        if performance:

            row = max(
                performance,
                key=lambda x: x["vistorias"],
            )

            return (
                f"🏢 A ECV com maior volume é "
                f"**{row['ecv']}**, com "
                f"**{_format_number(row['vistorias'])} "
                f"vistorias**."
            )

    return None


# ============================================================
# FALLBACK
# ============================================================

def _fallback_question_answer(
    question,
    summary,
):
    """
    Fallback seguro sem LLM.
    """

    kpis = summary["kpis"]

    performance = summary[
        "performance_ecv"
    ]

    anomalies = summary[
        "anomalias"
    ]

    # --------------------------------------------------------
    # ANOMALIAS
    # --------------------------------------------------------

    if (
        "anomalia" in question
        or "problema" in question
        or "alerta" in question
    ):

        if anomalies:

            linhas = []

            for item in anomalies[:5]:

                linhas.append(
                    f"- **{item['severidade'].upper()}** — "
                    f"{item['mensagem']}"
                )

            return (
                "### 🚨 Alertas identificados\n\n"
                + "\n".join(linhas)
            )

        return (
            "Não foram identificadas anomalias "
            "pelas regras operacionais configuradas."
        )

    # --------------------------------------------------------
    # RESULTADOS
    # --------------------------------------------------------

    if (
        "resultado" in question
        or "aprovação" in question
        or "reprovação" in question
    ):

        resultados = summary[
            "resultados"
        ]

        if resultados:

            linhas = []

            for item in resultados:

                linhas.append(
                    f"- **{item['nome']}:** "
                    f"{_format_number(item['quantidade'])}"
                )

            return (
                "### 📊 Distribuição dos resultados\n\n"
                + "\n".join(linhas)
            )

    # --------------------------------------------------------
    # CIDADES
    # --------------------------------------------------------

    if "cidade" in question:

        cidades = summary[
            "cidades"
        ]

        if cidades:

            maior = cidades[0]

            return (
                f"📍 A cidade com maior volume "
                f"é **{maior['nome']}**, com "
                f"**{_format_number(maior['quantidade'])} "
                f"vistorias**."
            )

    # --------------------------------------------------------
    # TIPOS
    # --------------------------------------------------------

    if (
        "tipo" in question
        and "vistoria" in question
    ):

        tipos = summary[
            "tipos_vistoria"
        ]

        if tipos:

            maior = tipos[0]

            return (
                f"📋 O tipo de vistoria com maior "
                f"volume é **{maior['nome']}**, com "
                f"**{_format_number(maior['quantidade'])} "
                f"registros**."
            )

    # --------------------------------------------------------
    # RESUMO
    # --------------------------------------------------------

    if performance:

        best = performance[0]

        worst = performance[-1]

        return (
            "### 📊 Resumo operacional\n\n"
            f"- Vistorias: **{_format_number(kpis['total'])}**\n"
            f"- ECVs: **{_format_number(kpis['ecvs'])}**\n"
            f"- Aprovação: **{kpis['taxa_aprovacao']:.1f}%**\n"
            f"- Reprovação: **{kpis['taxa_reprovacao']:.1f}%**\n"
            f"- Tempo médio: **{kpis['tempo_medio']:.1f} min**\n"
            f"- Faturamento: **{_format_money(kpis['faturamento'])}**\n\n"
            f"🏆 Melhor ECV: **{best['ecv']}** "
            f"({best['taxa_aprovacao']:.1f}%)\n\n"
            f"⚠️ Menor desempenho: **{worst['ecv']}** "
            f"({worst['taxa_aprovacao']:.1f}%)"
        )

    return (
        "Não foi possível responder à pergunta "
        "com segurança utilizando os dados disponíveis."
    )


# ============================================================
# INSIGHTS AUTOMÁTICOS
# ============================================================

def generate_insights(
    df,
) -> Dict[str, Any]:
    """
    Gera indicadores e insights estruturados.

    Essa função não depende da LLM.
    """

    summary = _build_data_summary(
        df
    )

    kpis = summary[
        "kpis"
    ]

    performance = summary[
        "performance_ecv"
    ]

    insights = []

    # --------------------------------------------------------
    # APROVAÇÃO
    # --------------------------------------------------------

    if kpis["taxa_aprovacao"] < 75:

        insights.append(
            {
                "tipo": "qualidade",
                "nivel": "alto",
                "titulo": "Taxa de aprovação abaixo do esperado",
                "mensagem": (
                    f"A taxa atual é de "
                    f"{kpis['taxa_aprovacao']:.1f}%."
                ),
            }
        )

    elif kpis["taxa_aprovacao"] >= 90:

        insights.append(
            {
                "tipo": "qualidade",
                "nivel": "baixo",
                "titulo": "Excelente taxa de aprovação",
                "mensagem": (
                    f"A operação apresenta "
                    f"{kpis['taxa_aprovacao']:.1f}% "
                    "de aprovação."
                ),
            }
        )

    # --------------------------------------------------------
    # TEMPO
    # --------------------------------------------------------

    if kpis["tempo_medio"] > DEFAULT_TEMPO_ALERTA:

        insights.append(
            {
                "tipo": "operacao",
                "nivel": "alto",
                "titulo": "Tempo operacional elevado",
                "mensagem": (
                    f"O tempo médio está em "
                    f"{kpis['tempo_medio']:.1f} minutos."
                ),
            }
        )

    # --------------------------------------------------------
    # PERFORMANCE
    # --------------------------------------------------------

    if performance:

        best = performance[0]

        worst = performance[-1]

        difference = (
            best["taxa_aprovacao"]
            - worst["taxa_aprovacao"]
        )

        insights.append(
            {
                "tipo": "performance",
                "nivel": "informativo",
                "titulo": "Diferença de desempenho entre ECVs",
                "mensagem": (
                    f"A diferença entre a melhor e a menor "
                    f"taxa de aprovação é de "
                    f"{difference:.1f} pontos percentuais."
                ),
            }
        )

    return {
        "kpis": kpis,
        "insights": insights,
        "anomalias": summary[
            "anomalias"
        ],
        "performance_ecv": performance,
    }


# ============================================================
# STATUS DA IA
# ============================================================

def get_ai_status() -> Dict[str, Any]:
    """
    Retorna status do motor de IA.
    """

    api_key = _get_api_key()

    return {
        "provider": "Google Gemini",
        "model": _get_model(),
        "configured": bool(api_key),
        "status": (
            "configured"
            if api_key
            else "not_configured"
        ),
        "features": {
            "copilot": True,
            "executive_analysis": True,
            "automatic_insights": True,
            "anomaly_detection": True,
            "ecv_ranking": True,
            "fallback_local": True,
        },
    }
```
