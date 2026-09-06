"""
ECV Intelligence V3
services/ai_service.py

Serviço de Inteligência Artificial do ECV Intelligence.

Responsabilidades:
- integração com Google Gemini;
- análise executiva dos KPIs;
- Copilot de dados;
- respostas baseadas nos dados reais;
- fallback local quando a API não estiver disponível;
- proteção contra respostas inventadas;
- tratamento de erros;
- controle básico de tamanho do contexto.

Compatível com:
    app.py V3
    services/analytics.py V3
"""

import json
import os
import re
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st
from google import genai


# ============================================================
# CONFIGURAÇÃO
# ============================================================

DEFAULT_MODEL = "gemini-2.5-flash"

MAX_ROWS_CONTEXT = 120
MAX_TEXT_LENGTH = 12000


# ============================================================
# CLIENT GEMINI
# ============================================================

def _get_api_key() -> Optional[str]:
    """
    Obtém a chave do Gemini.

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
    Permite alterar o modelo através de variável de ambiente.
    """

    return (
        os.getenv(
            "GEMINI_MODEL",
            DEFAULT_MODEL,
        ).strip()
        or DEFAULT_MODEL
    )


def _get_gemini_client():
    """
    Cria o cliente Gemini.

    Retorna:
        genai.Client ou None
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

def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _format_number(value):
    """
    Formata números no padrão brasileiro.
    """

    try:
        return f"{float(value):,.0f}".replace(
            ",",
            ".",
        )
    except (TypeError, ValueError):
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
    except (TypeError, ValueError):
        return "R$ 0,00"


def _clean_text(text):
    """
    Limita tamanho da resposta.
    """

    if not text:
        return ""

    text = str(text).strip()

    if len(text) > MAX_TEXT_LENGTH:
        return text[:MAX_TEXT_LENGTH].rstrip() + "..."

    return text


def _normalize_question(question):
    """
    Normaliza a pergunta do usuário.
    """

    return re.sub(
        r"\s+",
        " ",
        str(question or "").strip().lower(),
    )


# ============================================================
# PAYLOAD EXECUTIVO
# ============================================================

def _build_analysis_payload(kpi, perf):
    """
    Constrói payload seguro para análise da IA.
    """

    performance = []

    if isinstance(perf, pd.DataFrame):

        for row in perf.to_dict(
            orient="records"
        ):

            performance.append(
                {
                    key: (
                        value.item()
                        if hasattr(value, "item")
                        else value
                    )
                    for key, value in row.items()
                }
            )

    elif isinstance(perf, list):

        performance = perf

    return {
        "kpis": kpi or {},
        "performance": performance,
    }


# ============================================================
# ANÁLISE EXECUTIVA
# ============================================================

def analyze_data(kpi, perf):
    """
    Gera uma análise executiva utilizando os KPIs e
    desempenho das ECVs.

    Se Gemini estiver indisponível, utiliza análise local.
    """

    payload = _build_analysis_payload(
        kpi,
        perf,
    )

    client = _get_gemini_client()

    if client:

        prompt = f"""
Você é o módulo de Inteligência de Dados do ECV Intelligence,
uma plataforma SaaS de gestão e análise operacional para
Empresas Credenciadas de Vistoria (ECVs).

Analise EXCLUSIVAMENTE os dados fornecidos.

REGRAS IMPORTANTES:

1. Não invente números.
2. Não crie informações que não estejam nos dados.
3. Não faça afirmações que não possam ser sustentadas pelos dados.
4. Se alguma informação não estiver disponível, diga claramente
   que ela não está disponível.
5. Use os nomes reais das ECVs.
6. Utilize os percentuais exatamente conforme os dados.
7. Seja objetivo e profissional.
8. Não mencione que você é um modelo de IA.
9. Não inclua informações jurídicas ou regulatórias que não
   estejam presentes nos dados.

Estruture a resposta em Markdown:

### 📊 Visão Geral

Apresente:
- volume de vistorias;
- aprovação;
- reprovação;
- tempo médio;
- faturamento.

### 🔎 Destaques Operacionais

Identifique:
- melhor ECV;
- pior ECV;
- diferença de desempenho;
- possíveis pontos de atenção.

### 💡 Recomendação Gerencial

Apresente até 3 recomendações práticas baseadas
exclusivamente nos indicadores.

Dados:

{json.dumps(
    payload,
    ensure_ascii=False,
    default=str,
)}
"""

        try:

            response = client.models.generate_content(
                model=_get_model(),
                contents=prompt,
            )

            if response and response.text:

                return _clean_text(
                    response.text
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

def _local_executive_analysis(kpi, perf):
    """
    Análise local caso Gemini não esteja disponível.
    """

    kpi = kpi or {}

    total = kpi.get(
        "total",
        0,
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

    if (
        not isinstance(
            perf,
            pd.DataFrame,
        )
        or perf.empty
    ):

        return f"""
### 📊 Visão Geral

Foram analisadas **{_format_number(total)} vistorias**.

- **Taxa de aprovação:** {taxa_aprovacao:.1f}%
- **Taxa de reprovação:** {taxa_reprovacao:.1f}%
- **Tempo médio:** {tempo_medio:.1f} minutos
- **Faturamento:** {_format_money(faturamento)}

### 🔎 Destaques Operacionais

Não existem dados suficientes de desempenho por ECV para gerar um ranking.

### 💡 Recomendação Gerencial

Ampliar a análise por ECV, tipo de vistoria e período para identificar oportunidades operacionais.
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

### 💡 Recomendação Gerencial

Os dados de desempenho por ECV ainda não possuem todas as informações necessárias para um ranking.
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

        return "Não existem dados suficientes para gerar a análise."

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

Foram analisadas **{_format_number(total)} vistorias** no período disponível.

- **Taxa de aprovação:** {taxa_aprovacao:.1f}%
- **Taxa de reprovação:** {taxa_reprovacao:.1f}%
- **Tempo médio:** {tempo_medio:.1f} minutos
- **Faturamento:** {_format_money(faturamento)}

### 🔎 Destaques Operacionais

- **Melhor desempenho:** {best["ecv"]} — {best_rate:.1f}% de aprovação.
- **Menor desempenho:** {worst["ecv"]} — {worst_rate:.1f}% de aprovação.
- **Diferença:** {difference:.1f} pontos percentuais.

### 💡 Recomendação Gerencial

1. Avaliar os fatores associados às reprovações da unidade com menor desempenho.
2. Comparar o tempo médio de atendimento entre as ECVs.
3. Acompanhar periodicamente os indicadores para identificar tendências.
"""


# ============================================================
# RESUMO DOS DADOS
# ============================================================

def _build_data_summary(df):
    """
    Gera um resumo matemático da base.

    A IA recebe o resumo + amostra.
    Isso reduz o risco de responder com base somente
    nas primeiras linhas.
    """

    if df is None or df.empty:

        return {
            "total": 0,
            "ecvs": [],
            "resultados": {},
            "tipos_vistoria": {},
            "faturamento": 0,
            "tempo_medio": 0,
            "performance_ecv": [],
        }

    work = df.copy()

    total = len(work)

    # --------------------------------------------------------
    # RESULTADOS
    # --------------------------------------------------------

    resultados = {}

    if "resultado" in work.columns:

        resultados = (
            work["resultado"]
            .fillna("Não informado")
            .astype(str)
            .value_counts()
            .to_dict()
        )

    # --------------------------------------------------------
    # TIPOS
    # --------------------------------------------------------

    tipos = {}

    if "tipo_vistoria" in work.columns:

        tipos = (
            work["tipo_vistoria"]
            .fillna("Não informado")
            .astype(str)
            .value_counts()
            .to_dict()
        )

    # --------------------------------------------------------
    # FATURAMENTO
    # --------------------------------------------------------

    faturamento = 0.0

    if "valor" in work.columns:

        faturamento = _safe_float(
            pd.to_numeric(
                work["valor"],
                errors="coerce",
            ).sum()
        )

    # --------------------------------------------------------
    # TEMPO
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # ECVs
    # --------------------------------------------------------

    ecvs = []

    if "ecv" in work.columns:

        ecvs = sorted(
            work["ecv"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

    # --------------------------------------------------------
    # PERFORMANCE
    # --------------------------------------------------------

    performance = []

    if (
        "ecv" in work.columns
        and "resultado" in work.columns
    ):

        grouped = (
            work.groupby("ecv")
        )

        for ecv, group in grouped:

            total_ecv = len(group)

            approved = int(
                group["resultado"]
                .astype(str)
                .str.strip()
                .str.lower()
                .eq("aprovado")
                .sum()
            )

            rate = (
                approved
                / total_ecv
                * 100
                if total_ecv
                else 0
            )

            performance.append(
                {
                    "ecv": str(ecv),
                    "vistorias": total_ecv,
                    "aprovadas": approved,
                    "taxa_aprovacao": round(
                        rate,
                        2,
                    ),
                }
            )

        performance.sort(
            key=lambda x: x["taxa_aprovacao"],
            reverse=True,
        )

    return {
        "total": total,
        "ecvs": ecvs,
        "resultados": resultados,
        "tipos_vistoria": tipos,
        "faturamento": round(
            faturamento,
            2,
        ),
        "tempo_medio": round(
            tempo_medio,
            2,
        ),
        "performance_ecv": performance,
    }


# ============================================================
# COPILOT
# ============================================================

def ask_data(question, df):
    """
    Responde perguntas sobre a base operacional.

    Estratégia:

    1. Calcula resumo real da base.
    2. Tenta responder diretamente perguntas comuns.
    3. Se necessário, utiliza Gemini.
    4. Mantém fallback local.
    """

    question = (
        str(question or "")
        .strip()
    )

    if not question:

        return (
            "Digite uma pergunta para consultar "
            "os dados operacionais."
        )

    if df is None or df.empty:

        return (
            "Não existem dados disponíveis "
            "para análise."
        )

    normalized = _normalize_question(
        question
    )

    summary = _build_data_summary(
        df
    )

    # ========================================================
    # PERGUNTAS DETERMINÍSTICAS
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

            sample = df.head(
                MAX_ROWS_CONTEXT
            ).copy()

            sample_text = sample.to_string(
                index=False
            )

            prompt = f"""
Você é o Copilot de Dados do ECV Intelligence.

Responda à pergunta do usuário usando EXCLUSIVAMENTE
os dados operacionais fornecidos.

REGRAS:

- Não invente números.
- Não estime valores que não estejam disponíveis.
- Não crie nomes de ECVs.
- Não faça afirmações sem evidência nos dados.
- Para totais, utilize o resumo calculado.
- Se a pergunta não puder ser respondida pelos dados,
  explique isso claramente.
- Seja direto.
- Responda em português do Brasil.
- Utilize Markdown quando melhorar a leitura.

RESUMO CALCULADO DA BASE:

{json.dumps(
    summary,
    ensure_ascii=False,
    default=str,
)}

AMOSTRA DOS REGISTROS:

{sample_text}

PERGUNTA DO USUÁRIO:

{question}
"""

            response = client.models.generate_content(
                model=_get_model(),
                contents=prompt,
            )

            if response and response.text:

                return _clean_text(
                    response.text
                )

        except Exception:
            pass

    # ========================================================
    # FALLBACK
    # ========================================================

    return _fallback_question_answer(
        normalized,
        summary,
    )


# ============================================================
# PERGUNTAS COMUNS
# ============================================================

def _answer_common_question(
    question,
    summary,
):
    """
    Responde perguntas que podem ser calculadas
    sem IA generativa.
    """

    total = summary["total"]

    # --------------------------------------------------------
    # TOTAL DE VISTORIAS
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
            f"O conjunto atual possui "
            f"**{_format_number(total)} vistorias**."
        )

    # --------------------------------------------------------
    # QUANTIDADE DE ECV
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
            f"**{len(summary['ecvs'])} ECVs**."
        )

    # --------------------------------------------------------
    # FATURAMENTO
    # --------------------------------------------------------

    if (
        "faturamento" in question
        or "receita" in question
    ):

        return (
            f"O faturamento registrado na base é "
            f"**{_format_money(summary['faturamento'])}**."
        )

    # --------------------------------------------------------
    # MELHOR ECV
    # --------------------------------------------------------

    if (
        "melhor" in question
        and (
            "ecv" in question
            or "desempenho" in question
            or "aprovação" in question
        )
    ):

        performance = summary[
            "performance_ecv"
        ]

        if performance:

            row = performance[0]

            return (
                f"**{row['ecv']}** apresentou a "
                f"maior taxa de aprovação: "
                f"**{row['taxa_aprovacao']:.1f}%**."
            )

    # --------------------------------------------------------
    # PIOR ECV
    # --------------------------------------------------------

    if (
        "pior" in question
        and (
            "ecv" in question
            or "desempenho" in question
            or "reprovação" in question
        )
    ):

        performance = summary[
            "performance_ecv"
        ]

        if performance:

            row = performance[-1]

            return (
                f"**{row['ecv']}** apresentou a "
                f"menor taxa de aprovação: "
                f"**{row['taxa_aprovacao']:.1f}%**."
            )

    return None


# ============================================================
# FALLBACK DO COPILOT
# ============================================================

def _fallback_question_answer(
    question,
    summary,
):
    """
    Resposta segura quando Gemini não está disponível
    e a pergunta não pertence às regras determinísticas.
    """

    performance = summary[
        "performance_ecv"
    ]

    if (
        "tempo" in question
        and "médio" in question
    ):

        return (
            f"O tempo médio registrado é "
            f"**{summary['tempo_medio']:.1f} minutos**."
        )

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

            for nome, quantidade in resultados.items():

                linhas.append(
                    f"- **{nome}:** "
                    f"{_format_number(quantidade)}"
                )

            return (
                "### Distribuição dos resultados\n\n"
                + "\n".join(linhas)
            )

    if performance:

        best = performance[0]
        worst = performance[-1]

        return (
            "Consigo analisar os dados operacionais. "
            "Alguns indicadores disponíveis são:\n\n"
            f"- Total: **{_format_number(summary['total'])} vistorias**\n"
            f"- ECVs: **{len(summary['ecvs'])}**\n"
            f"- Faturamento: **{_format_money(summary['faturamento'])}**\n"
            f"- Melhor ECV: **{best['ecv']}** "
            f"({best['taxa_aprovacao']:.1f}% aprovação)\n"
            f"- Menor ECV: **{worst['ecv']}** "
            f"({worst['taxa_aprovacao']:.1f}% aprovação)"
        )

    return (
        "Não foi possível encontrar uma resposta "
        "determinística para essa pergunta com os "
        "dados disponíveis."
    )


# ============================================================
# STATUS DA IA
# ============================================================

def get_ai_status() -> Dict[str, Any]:
    """
    Retorna informações do estado do serviço de IA.

    Útil para futuras telas de administração.
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
    }
