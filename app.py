import html
import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import requests
import streamlit as st


# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="ECV Intelligence",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_URL = os.getenv(
    "ECV_API_URL",
    "https://ecv-intelligence-api-v3.onrender.com"
).rstrip("/")

API_TIMEOUT = int(
    os.getenv("ECV_API_TIMEOUT", "30")
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
<style>

.stApp{
    background:#0f172a;
    color:#f8fafc;
}

[data-testid="stSidebar"]{
    background:#0b1120;
    border-right:1px solid rgba(255,255,255,.08);
    min-width:285px!important;
    max-width:285px!important;
}

[data-testid="stSidebar"] *{
    color:#f8fafc!important;
}

#MainMenu,
footer{
    visibility:hidden;
}

.block-container{
    padding:1.5rem 2rem 2.5rem;
    max-width:100%!important;
}


/* ========================================================
   HERO
   ======================================================== */

.hero{
    padding:1.5rem 1.8rem;
    border:1px solid rgba(255,255,255,.08);
    border-radius:16px;
    background:#1e293b;
    margin-bottom:1.2rem;
}

.hero h1{
    margin:0;
    font-size:2rem;
    color:#f8fafc;
}

.hero p{
    margin:.45rem 0 0;
    color:#94a3b8;
}


/* ========================================================
   SECTIONS
   ======================================================== */

.section-title{
    font-size:1.1rem;
    font-weight:700;
    margin:1.2rem 0 .8rem;
}


/* ========================================================
   METRICS
   ======================================================== */

[data-testid="stMetric"]{
    border:1px solid rgba(255,255,255,.08);
    border-radius:14px;
    padding:14px 16px;
    background:#1e293b;
}

[data-testid="stMetric"] label{
    color:#94a3b8!important;
}

[data-testid="stMetric"] [data-testid="stMetricValue"]{
    color:#f8fafc!important;
}


/* ========================================================
   CARDS
   ======================================================== */

.card{
    border:1px solid rgba(255,255,255,.08);
    border-radius:14px;
    padding:1.2rem 1.3rem;
    background:#1e293b;
    color:#f8fafc;
}

.badge{
    display:inline-block;
    padding:.22rem .55rem;
    border-radius:999px;
    font-size:.72rem;
    font-weight:700;
    background:#334155;
}

.small{
    font-size:.82rem;
    color:#94a3b8;
}

.success{
    color:#4ade80;
}

.danger{
    color:#f87171;
}


/* ========================================================
   API STATUS
   ======================================================== */

.api-online{
    color:#4ade80!important;
    font-weight:700;
}

.api-offline{
    color:#f87171!important;
    font-weight:700;
}


/* ========================================================
   SIDEBAR PROFISSIONAL
   ======================================================== */

.sidebar-brand{
    padding:8px 0 14px 0;
}

.sidebar-brand h2{
    margin:0;
    font-size:1.15rem;
    font-weight:700;
}

.sidebar-brand p{
    margin:4px 0 0;
    color:#94a3b8!important;
    font-size:.75rem;
    line-height:1.4;
}

.sidebar-section{
    margin-top:8px;
    margin-bottom:5px;
    padding:0 2px;
    font-size:.68rem;
    font-weight:800;
    letter-spacing:.08em;
    color:#64748b!important;
}

.sidebar-info{
    border:1px solid rgba(255,255,255,.07);
    border-radius:10px;
    padding:10px 11px;
    background:rgba(30,41,59,.55);
    margin-top:7px;
}

.sidebar-info-title{
    font-size:.72rem;
    font-weight:700;
    color:#94a3b8!important;
    margin-bottom:5px;
}

.sidebar-info-value{
    font-size:.78rem;
    color:#f8fafc!important;
    word-break:break-word;
}

.sidebar-status{
    border-radius:10px;
    padding:9px 11px;
    margin-top:7px;
    background:rgba(30,41,59,.55);
    border:1px solid rgba(255,255,255,.07);
}

.sidebar-status-label{
    font-size:.68rem;
    color:#64748b!important;
    margin-bottom:3px;
}

.sidebar-status-value{
    font-size:.8rem;
    font-weight:700;
}

.sidebar-footer{
    text-align:center;
    color:#64748b!important;
    font-size:.68rem;
    padding:8px 0;
}


/* ========================================================
   BUTTONS
   ======================================================== */

.stButton > button{
    border-radius:9px;
}


/* ========================================================
   DATAFRAME
   ======================================================== */

[data-testid="stDataFrame"]{
    border-radius:12px;
}


/* ========================================================
   LINKS
   ======================================================== */

a{
    color:#60a5fa;
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS
# ============================================================

def number(value):
    try:
        return f"{float(value):,.0f}".replace(",", ".")
    except Exception:
        return "0"


def money(value):
    try:
        return (
            f"R$ {float(value):,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )
    except Exception:
        return "R$ 0,00"


def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def normalize_list_response(
    data,
    possible_keys=None,
):
    """
    Converte respostas da API em lista de registros.

    Aceita:

        [...]
        {"data": [...]}
        {"items": [...]}
        {"results": [...]}
        {"records": [...]}
        {"ecvs": [...]}
        {"vistorias": [...]}
    """

    if isinstance(data, list):
        return data

    if isinstance(data, dict):

        keys = possible_keys or [
            "data",
            "items",
            "results",
            "records",
            "ecvs",
            "vistorias",
        ]

        for key in keys:

            value = data.get(key)

            if isinstance(value, list):
                return value

    return []


# ============================================================
# CLIENTE DA API
# ============================================================

@st.cache_data(
    ttl=30,
    show_spinner=False,
)
def api_get(
    endpoint,
    params=None,
):
    """
    Cliente HTTP centralizado da API.
    """

    url = f"{API_URL}{endpoint}"

    try:

        response = requests.get(
            url,
            params=params,
            timeout=API_TIMEOUT,
            headers={
                "Accept": "application/json",
                "User-Agent": (
                    "ECV-Intelligence-Streamlit/3.1"
                ),
            },
        )

        response.raise_for_status()

        return {
            "ok": True,
            "status_code": response.status_code,
            "data": response.json(),
            "error": None,
        }

    except requests.exceptions.Timeout:

        return {
            "ok": False,
            "status_code": None,
            "data": None,
            "error": (
                "Tempo limite excedido ao "
                "consultar a API."
            ),
        }

    except requests.exceptions.ConnectionError:

        return {
            "ok": False,
            "status_code": None,
            "data": None,
            "error": (
                "Não foi possível conectar à API."
            ),
        }

    except requests.exceptions.HTTPError as exc:

        return {
            "ok": False,
            "status_code": getattr(
                exc.response,
                "status_code",
                None,
            ),
            "data": None,
            "error": (
                f"Erro HTTP na API: {exc}"
            ),
        }

    except Exception as exc:

        return {
            "ok": False,
            "status_code": None,
            "data": None,
            "error": str(exc),
        }


# ============================================================
# ENDPOINTS
# ============================================================

def get_api_health():
    return api_get("/health")


def get_api_status():
    return api_get("/status")


def get_api_dashboard():
    return api_get("/dashboard")


def get_api_indicadores():
    return api_get("/indicadores")


def get_api_vistorias():
    return api_get("/vistorias")


def get_api_ecvs():
    return api_get("/ecvs")


def get_api_analytics_ecvs():
    return api_get("/analytics/ecvs")


def get_api_quality():
    return api_get("/analytics/quality")


def get_api_daily():
    return api_get("/analytics/daily")


def get_api_automations():
    return api_get("/automations")


# ============================================================
# NORMALIZAÇÃO
# ============================================================

def build_vistorias_dataframe(data):

    records = normalize_list_response(
        data,
        [
            "vistorias",
            "data",
            "items",
            "results",
            "records",
        ],
    )

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)

    rename_map = {
        "date": "data_vistoria",
        "data": "data_vistoria",
        "type": "tipo_vistoria",
        "result": "resultado",
        "time": "tempo_minutos",
        "amount": "valor",
        "ecv_nome": "ecv",
        "nome_ecv": "ecv",
    }

    df = df.rename(
        columns=rename_map
    )

    if "data_vistoria" in df.columns:

        df["data_dt"] = pd.to_datetime(
            df["data_vistoria"],
            errors="coerce",
        )

    return df


def build_ecvs_dataframe(data):

    records = normalize_list_response(
        data,
        [
            "ecvs",
            "data",
            "items",
            "results",
            "records",
        ],
    )

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records)


def build_daily_dataframe(data):

    records = normalize_list_response(
        data,
        [
            "daily",
            "data",
            "items",
            "results",
            "records",
        ],
    )

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)

    rename_map = {
        "date": "data",
        "total": "vistorias",
        "count": "vistorias",
    }

    df = df.rename(
        columns=rename_map
    )

    return df


def build_performance_dataframe(data):

    records = normalize_list_response(
        data,
        [
            "ecvs",
            "performance",
            "data",
            "items",
            "results",
            "records",
        ],
    )

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)

    rename_map = {
        "nome": "ecv",
        "ecv_nome": "ecv",
        "approval_rate": "taxa_aprovacao",
        "taxa_aprovacao_percentual": (
            "taxa_aprovacao"
        ),
    }

    df = df.rename(
        columns=rename_map
    )

    if "taxa_aprovacao" in df.columns:

        df["taxa_aprovacao"] = pd.to_numeric(
            df["taxa_aprovacao"],
            errors="coerce",
        ).fillna(0)

    return df


# ============================================================
# CARREGAMENTO PRINCIPAL
# ============================================================

with st.spinner(
    "Conectando à ECV Intelligence API..."
):

    health = get_api_health()

    status_api = get_api_status()

    dashboard_response = (
        get_api_dashboard()
    )

    indicadores_response = (
        get_api_indicadores()
    )

    vistorias_response = (
        get_api_vistorias()
    )

    ecvs_response = (
        get_api_ecvs()
    )

    performance_response = (
        get_api_analytics_ecvs()
    )

    quality_response = (
        get_api_quality()
    )

    daily_response = (
        get_api_daily()
    )

    automations_response = (
        get_api_automations()
    )


api_online = health.get(
    "ok",
    False,
)


# ============================================================
# SIDEBAR — 5 BLOCOS
# ============================================================

with st.sidebar:

    # --------------------------------------------------------
    # MARCA
    # --------------------------------------------------------

    st.markdown(
        """
<div class="sidebar-brand">

<h2>📊 ECV Intelligence</h2>

<p>
Analytics, IA e automação
para Empresas Credenciadas
de Vistoria.
</p>

</div>
""",
        unsafe_allow_html=True,
    )

    st.divider()


    # ========================================================
    # 1. WORKSPACE
    # ========================================================

    st.markdown(
        '<div class="sidebar-section">'
        'WORKSPACE'
        '</div>',
        unsafe_allow_html=True,
    )

    workspace_page = st.radio(
        "Workspace",
        [
            "📊 Visão Geral",
        ],
        label_visibility="collapsed",
        key="workspace_navigation",
    )


    # ========================================================
    # 2. INTELIGÊNCIA
    # ========================================================

    st.markdown(
        '<div class="sidebar-section">'
        'INTELIGÊNCIA'
        '</div>',
        unsafe_allow_html=True,
    )

    intelligence_page = st.radio(
        "Inteligência",
        [
            "✨ IA & Insights",
        ],
        label_visibility="collapsed",
        key="intelligence_navigation",
    )


    # ========================================================
    # 3. INTEGRAÇÕES
    # ========================================================

    st.markdown(
        '<div class="sidebar-section">'
        'INTEGRAÇÕES'
        '</div>',
        unsafe_allow_html=True,
    )

    integrations_page = st.radio(
        "Integrações",
        [
            "🔌 API & Integrações",
        ],
        label_visibility="collapsed",
        key="integrations_navigation",
    )


    # ========================================================
    # 4. GESTÃO
    # ========================================================

    st.markdown(
        '<div class="sidebar-section">'
        'GESTÃO'
        '</div>',
        unsafe_allow_html=True,
    )

    management_page = st.radio(
        "Gestão",
        [
            "🚗 Vistorias",
            "🏢 ECVs",
            "✓ Qualidade",
            "⚙️ Automações",
        ],
        label_visibility="collapsed",
        key="management_navigation",
    )


    # ========================================================
    # DETERMINAÇÃO DA PÁGINA
    # ========================================================

    if workspace_page == "📊 Visão Geral":

        page = "Visão Geral"

    elif intelligence_page == "✨ IA & Insights":

        page = "IA & Insights"

    elif integrations_page == "🔌 API & Integrações":

        page = "API"

    elif management_page == "🚗 Vistorias":

        page = "Vistorias"

    elif management_page == "🏢 ECVs":

        page = "ECVs"

    elif management_page == "✓ Qualidade":

        page = "Qualidade"

    elif management_page == "⚙️ Automações":

        page = "Automações"

    else:

        page = "Visão Geral"


    st.divider()


    # ========================================================
    # 5. AMBIENTE / CONTA
    # ========================================================

    st.markdown(
        '<div class="sidebar-section">'
        'AMBIENTE / CONTA'
        '</div>',
        unsafe_allow_html=True,
    )


    # --------------------------------------------------------
    # STATUS DA API
    # --------------------------------------------------------

    if api_online:

        st.markdown(
            """
<div class="sidebar-status">

<div class="sidebar-status-label">
STATUS DO SISTEMA
</div>

<div class="sidebar-status-value api-online">
● API ONLINE
</div>

</div>
""",
            unsafe_allow_html=True,
        )

    else:

        st.markdown(
            """
<div class="sidebar-status">

<div class="sidebar-status-label">
STATUS DO SISTEMA
</div>

<div class="sidebar-status-value api-offline">
● API OFFLINE
</div>

</div>
""",
            unsafe_allow_html=True,
        )


    # --------------------------------------------------------
    # PRODUTO
    # --------------------------------------------------------

    st.markdown(
        """
<div class="sidebar-info">

<div class="sidebar-info-title">
PRODUTO
</div>

<div class="sidebar-info-value">
ECV Intelligence API V3
</div>

</div>
""",
        unsafe_allow_html=True,
    )


    # --------------------------------------------------------
    # PLANO
    # --------------------------------------------------------

    st.markdown(
        """
<div class="sidebar-info">

<div class="sidebar-info-title">
PLANO
</div>

<div class="sidebar-info-value">
Demo
</div>

</div>
""",
        unsafe_allow_html=True,
    )


    # --------------------------------------------------------
    # FRONTEND
    # --------------------------------------------------------

    st.markdown(
        """
<div class="sidebar-info">

<div class="sidebar-info-title">
FRONTEND
</div>

<div class="sidebar-info-value">
Streamlit V3.1
</div>

</div>
""",
        unsafe_allow_html=True,
    )


    # --------------------------------------------------------
    # BACKEND
    # --------------------------------------------------------

    st.markdown(
        """
<div class="sidebar-info">

<div class="sidebar-info-title">
BACKEND
</div>

<div class="sidebar-info-value">
FastAPI + Analytics + IA
</div>

</div>
""",
        unsafe_allow_html=True,
    )


    # --------------------------------------------------------
    # API
    # --------------------------------------------------------

    st.markdown(
        f"""
<div class="sidebar-info">

<div class="sidebar-info-title">
API
</div>

<div class="sidebar-info-value">
{html.escape(API_URL)}
</div>

</div>
""",
        unsafe_allow_html=True,
    )


    # --------------------------------------------------------
    # ATUALIZAÇÃO
    # --------------------------------------------------------

    st.markdown(
        "<div style='height:6px'></div>",
        unsafe_allow_html=True,
    )

    if st.button(
        "🔄 Atualizar dados",
        use_container_width=True,
    ):

        st.cache_data.clear()

        st.rerun()


    # --------------------------------------------------------
    # VERSÃO
    # --------------------------------------------------------

    st.markdown(
        """
<div class="sidebar-footer">
ECV Intelligence V3.1<br>
SaaS Analytics Platform
</div>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# DADOS
# ============================================================

df = build_vistorias_dataframe(
    vistorias_response.get("data")
)

ecvs_df = build_ecvs_dataframe(
    ecvs_response.get("data")
)

perf = build_performance_dataframe(
    performance_response.get("data")
)

daily = build_daily_dataframe(
    daily_response.get("data")
)


# ============================================================
# VALIDAÇÃO DA API
# ============================================================

if not api_online:

    st.error(
        "A API ECV Intelligence está indisponível "
        "no momento. Verifique o serviço no Render."
    )

    st.link_button(
        "🌐 Abrir API",
        API_URL,
        use_container_width=True,
    )

    st.stop()


if df.empty:

    st.warning(
        "A API está online, mas não retornou "
        "registros de vistorias."
    )


# ============================================================
# KPI
# ============================================================

dashboard_data = (
    dashboard_response.get("data")
    or {}
)

indicadores_data = (
    indicadores_response.get("data")
    or {}
)


def extract_kpi(
    keys,
    default=0,
):

    for source in [
        dashboard_data,
        indicadores_data,
    ]:

        if isinstance(source, dict):

            for key in keys:

                if key in source:

                    return source[key]

    return default


total_vistorias = extract_kpi(
    [
        "total_vistorias",
        "vistorias",
        "total",
    ],
    len(df),
)


taxa_aprovacao = extract_kpi(
    [
        "taxa_aprovacao",
        "approval_rate",
    ],
    0,
)


taxa_reprovacao = extract_kpi(
    [
        "taxa_reprovacao",
        "rejection_rate",
    ],
    0,
)


tempo_medio = extract_kpi(
    [
        "tempo_medio",
        "tempo_medio_minutos",
        "average_time",
    ],
    0,
)


faturamento = extract_kpi(
    [
        "faturamento",
        "receita",
        "revenue",
    ],
    0,
)


# ============================================================
# VISÃO GERAL
# ============================================================

if page == "Visão Geral":

    st.markdown(
        """
<div class="hero">

<h1>Visão Executiva</h1>

<p>
Monitoramento operacional, desempenho das ECVs
e inteligência para tomada de decisão.
</p>

</div>
""",
        unsafe_allow_html=True,
    )


    c1, c2, c3, c4, c5 = st.columns(5)


    c1.metric(
        "Vistorias",
        number(total_vistorias),
    )


    c2.metric(
        "Aprovação",
        f"{safe_float(taxa_aprovacao):.1f}%",
    )


    c3.metric(
        "Reprovação",
        f"{safe_float(taxa_reprovacao):.1f}%",
    )


    c4.metric(
        "Tempo médio",
        f"{safe_float(tempo_medio):.1f} min",
    )


    c5.metric(
        "Faturamento",
        money(faturamento),
    )


    st.markdown(
        '<div class="section-title">'
        'Performance operacional'
        '</div>',
        unsafe_allow_html=True,
    )


    a, b = st.columns(2)


    # --------------------------------------------------------
    # GRÁFICO DIÁRIO
    # --------------------------------------------------------

    if (
        not daily.empty
        and "data" in daily.columns
    ):

        daily["data"] = pd.to_datetime(
            daily["data"],
            errors="coerce",
        )

        if "vistorias" in daily.columns:

            fig1 = px.line(
                daily,
                x="data",
                y="vistorias",
                markers=True,
                title=(
                    "Volume diário de vistorias"
                ),
            )

            fig1.update_layout(
                plot_bgcolor="#1e293b",
                paper_bgcolor="#1e293b",
                font=dict(
                    color="#94a3b8"
                ),
                margin=dict(
                    l=20,
                    r=20,
                    t=50,
                    b=30,
                ),
            )

            a.plotly_chart(
                fig1,
                use_container_width=True,
            )


    # --------------------------------------------------------
    # PERFORMANCE ECV
    # --------------------------------------------------------

    if (
        not perf.empty
        and "ecv" in perf.columns
        and "taxa_aprovacao" in perf.columns
    ):

        fig2 = px.bar(
            perf,
            x="ecv",
            y="taxa_aprovacao",
            text_auto=".1f",
            title=(
                "Taxa de aprovação por ECV (%)"
            ),
        )

        fig2.update_layout(
            plot_bgcolor="#1e293b",
            paper_bgcolor="#1e293b",
            font=dict(
                color="#94a3b8"
            ),
            margin=dict(
                l=20,
                r=20,
                t=50,
                b=30,
            ),
            showlegend=False,
        )

        b.plotly_chart(
            fig2,
            use_container_width=True,
        )


    # --------------------------------------------------------
    # DESEMPENHO
    # --------------------------------------------------------

    if (
        not perf.empty
        and "taxa_aprovacao" in perf.columns
    ):

        perf = (
            perf
            .sort_values(
                "taxa_aprovacao",
                ascending=False,
            )
            .reset_index(drop=True)
        )

        best = perf.iloc[0]

        worst = perf.iloc[-1]

        x, y, z = st.columns(3)


        x.markdown(
            f"""
<div class="card">

<span class="badge">
MELHOR DESEMPENHO
</span>

<h3>
{html.escape(
    str(best.get("ecv", "N/D"))
)}
</h3>

<div class="success">
{safe_float(
    best.get("taxa_aprovacao")
):.1f}% de aprovação
</div>

</div>
""",
            unsafe_allow_html=True,
        )


        y.markdown(
            f"""
<div class="card">

<span class="badge">
PONTO DE ATENÇÃO
</span>

<h3>
{html.escape(
    str(worst.get("ecv", "N/D"))
)}
</h3>

<div class="danger">
{safe_float(
    worst.get("taxa_aprovacao")
):.1f}% de aprovação
</div>

</div>
""",
            unsafe_allow_html=True,
        )


        diferenca = (
            safe_float(
                best.get(
                    "taxa_aprovacao"
                )
            )
            -
            safe_float(
                worst.get(
                    "taxa_aprovacao"
                )
            )
        )


        z.markdown(
            f"""
<div class="card">

<span class="badge">
DIFERENCIAL
</span>

<h3>
{diferenca:.1f} p.p.
</h3>

<div class="small">
Distância entre melhor e pior ECV.
</div>

</div>
""",
            unsafe_allow_html=True,
        )


# ============================================================
# VISTORIAS
# ============================================================

elif page == "Vistorias":

    st.markdown(
        """
<div class="hero">

<h1>Vistorias</h1>

<p>
Pesquisa, filtros e exportação dos
registros operacionais.
</p>

</div>
""",
        unsafe_allow_html=True,
    )


    if df.empty:

        st.info(
            "Nenhuma vistoria disponível."
        )

        st.stop()


    if "data_dt" not in df.columns:

        df["data_dt"] = pd.to_datetime(
            df.get(
                "data_vistoria"
            ),
            errors="coerce",
        )


    valid_dates = (
        df["data_dt"]
        .dropna()
    )


    if not valid_dates.empty:

        mn = (
            valid_dates
            .min()
            .date()
        )

        mx = (
            valid_dates
            .max()
            .date()
        )


        c1, c2, c3 = st.columns(3)


        with c1:

            periodo = st.date_input(
                "Período",
                [mn, mx],
                min_value=mn,
                max_value=mx,
            )


        with c2:

            ecv_values = (
                sorted(
                    df["ecv"]
                    .dropna()
                    .unique()
                    .tolist()
                )
                if "ecv" in df.columns
                else []
            )

            ef = st.selectbox(
                "ECV",
                ["Todas"] + ecv_values,
            )


        with c3:

            city_values = (
                sorted(
                    df["cidade"]
                    .dropna()
                    .unique()
                    .tolist()
                )
                if "cidade" in df.columns
                else []
            )

            cf = st.selectbox(
                "Cidade",
                ["Todas"] + city_values,
            )


        c4, c5, c6 = st.columns(3)


        with c4:

            tipos = (
                sorted(
                    df["tipo_vistoria"]
                    .dropna()
                    .unique()
                    .tolist()
                )
                if "tipo_vistoria"
                in df.columns
                else []
            )

            tf = st.multiselect(
                "Tipo",
                tipos,
                default=tipos,
            )


        with c5:

            resultados = (
                sorted(
                    df["resultado"]
                    .dropna()
                    .unique()
                    .tolist()
                )
                if "resultado"
                in df.columns
                else []
            )

            rf = st.multiselect(
                "Resultado",
                resultados,
                default=resultados,
            )


        with c6:

            busca = st.text_input(
                "Buscar",
                "",
                placeholder="Placa ou ID",
            )


        f = df.copy()


        if (
            isinstance(
                periodo,
                (list, tuple)
            )
            and len(periodo) == 2
        ):

            f = f[
                (
                    f.data_dt.dt.date
                    >= periodo[0]
                )
                &
                (
                    f.data_dt.dt.date
                    <= periodo[1]
                )
            ]


        if (
            ef != "Todas"
            and "ecv" in f.columns
        ):

            f = f[
                f.ecv == ef
            ]


        if (
            cf != "Todas"
            and "cidade" in f.columns
        ):

            f = f[
                f.cidade == cf
            ]


        if (
            tf
            and "tipo_vistoria"
            in f.columns
        ):

            f = f[
                f.tipo_vistoria
                .isin(tf)
            ]


        if (
            rf
            and "resultado"
            in f.columns
        ):

            f = f[
                f.resultado
                .isin(rf)
            ]


        if busca:

            q = (
                busca
                .lower()
                .strip()
            )

            mask = pd.Series(
                False,
                index=f.index,
            )


            if "placa" in f.columns:

                mask = (
                    mask
                    |
                    f["placa"]
                    .astype(str)
                    .str.lower()
                    .str.contains(
                        q,
                        na=False,
                    )
                )


            if "id" in f.columns:

                mask = (
                    mask
                    |
                    f["id"]
                    .astype(str)
                    .str.contains(
                        q,
                        na=False,
                    )
                )


            f = f[mask]


        a, b, c, d = st.columns(4)


        total = len(f)


        if "resultado" in f.columns:

            resultado_lower = (
                f["resultado"]
                .astype(str)
                .str.lower()
            )


            ap = int(
                (
                    resultado_lower
                    == "aprovado"
                ).sum()
            )


            rp = int(
                (
                    resultado_lower
                    == "reprovado"
                ).sum()
            )

        else:

            ap = 0
            rp = 0


        a.metric(
            "Registros",
            number(total),
        )


        b.metric(
            "Aprovação",
            (
                f"{ap / total * 100:.1f}%"
                if total
                else "0,0%"
            ),
        )


        c.metric(
            "Reprovação",
            (
                f"{rp / total * 100:.1f}%"
                if total
                else "0,0%"
            ),
        )


        faturamento_filtro = (
            pd.to_numeric(
                f["valor"],
                errors="coerce",
            )
            .fillna(0)
            .sum()
            if "valor" in f.columns
            else 0
        )


        d.metric(
            "Faturamento",
            money(
                faturamento_filtro
            ),
        )


        preferred_cols = [
            "id",
            "data_vistoria",
            "ecv",
            "cidade",
            "placa",
            "tipo_vistoria",
            "resultado",
            "tempo_minutos",
            "valor",
        ]


        cols = [
            col
            for col in preferred_cols
            if col in f.columns
        ]


        st.dataframe(
            f[cols],
            use_container_width=True,
            hide_index=True,
        )


        st.download_button(
            "📥 Exportar CSV",
            f.to_csv(
                index=False
            ).encode("utf-8"),
            "vistorias_filtradas.csv",
            "text/csv",
        )


# ============================================================
# QUALIDADE
# ============================================================

elif page == "Qualidade":

    st.markdown(
        """
<div class="hero">

<h1>Qualidade dos Dados</h1>

<p>
Diagnóstico da confiabilidade
da base operacional.
</p>

</div>
""",
        unsafe_allow_html=True,
    )


    quality_data = (
        quality_response.get(
            "data"
        )
        or {}
    )


    if isinstance(
        quality_data,
        dict
    ):

        total = quality_data.get(
            "total",
            quality_data.get(
                "registros",
                len(df),
            ),
        )


        duplicados = (
            quality_data.get(
                "duplicados",
                0,
            )
        )


        nulos = quality_data.get(
            "nulos",
            quality_data.get(
                "campos_vazios",
                0,
            ),
        )


        placas_invalidas = (
            quality_data.get(
                "placas_invalidas",
                0,
            )
        )


        a, b, c, d = st.columns(4)


        a.metric(
            "Registros",
            number(total),
        )


        b.metric(
            "Duplicados",
            number(duplicados),
        )


        c.metric(
            "Campos vazios",
            number(nulos),
        )


        d.metric(
            "Placas inválidas",
            number(placas_invalidas),
        )


        if safe_float(total) > 0:

            score = max(
                0,
                100
                -
                (
                    safe_float(
                        duplicados
                    )
                    +
                    safe_float(
                        nulos
                    )
                    +
                    safe_float(
                        placas_invalidas
                    )
                )
                /
                safe_float(total)
                *
                100,
            )

        else:

            score = 0


        st.markdown(
            f"""
<div class="card">

<span class="badge">
SCORE DE QUALIDADE
</span>

<h2>
{score:.1f}%
</h2>

<div class="small">
Calculado a partir das inconsistências
identificadas.
</div>

</div>
""",
            unsafe_allow_html=True,
        )


        mensagens = (
            quality_data.get(
                "mensagens",
                [],
            )
        )


        for msg in mensagens:

            st.write(msg)


    else:

        st.info(
            "A API não retornou dados "
            "de qualidade."
        )


# ============================================================
# AUTOMAÇÕES
# ============================================================

elif page == "Automações":

    st.markdown(
        """
<div class="hero">

<h1>Central de Automações</h1>

<p>
Monitoramento das regras e
execuções automatizadas.
</p>

</div>
""",
        unsafe_allow_html=True,
    )


    automation_data = (
        automations_response.get(
            "data"
        )
        if automations_response.get(
            "ok"
        )
        else None
    )


    logs = pd.DataFrame(
        normalize_list_response(
            automation_data,
            [
                "automations",
                "data",
                "items",
                "results",
                "logs",
            ],
        )
    )


    total = len(logs)


    if not logs.empty:

        status_column = None


        for candidate in [
            "status",
            "resultado",
            "state",
        ]:

            if candidate in logs.columns:

                status_column = candidate

                break


        if status_column:

            sucesso = int(
                logs[
                    status_column
                ]
                .astype(str)
                .str.lower()
                .isin(
                    [
                        "concluído",
                        "concluido",
                        "success",
                        "sucesso",
                        "completed",
                    ]
                )
                .sum()
            )

        else:

            sucesso = 0

    else:

        sucesso = 0


    taxa = (
        sucesso
        /
        total
        *
        100
        if total
        else 0
    )


    processados = 0


    if not logs.empty:

        for column in [
            "registros_processados",
            "processed",
            "processados",
        ]:

            if column in logs.columns:

                processados = int(
                    pd.to_numeric(
                        logs[column],
                        errors="coerce",
                    )
                    .fillna(0)
                    .sum()
                )

                break


    a, b, c, d = st.columns(4)


    a.metric(
        "Execuções",
        number(total),
    )


    b.metric(
        "Sucesso",
        f"{taxa:.1f}%",
    )


    c.metric(
        "Processados",
        number(processados),
    )


    d.metric(
        "Status",
        "Operacional"
        if api_online
        else "Offline",
    )


    st.markdown(
        """
<div class="card">

<span class="badge">
AUTOMATION ENGINE
</span>

<h3>
Pipeline operacional
</h3>

<div class="small">
Leitura → Validação →
Duplicidades → Campos críticos →
Indicadores → Log
</div>

</div>
""",
        unsafe_allow_html=True,
    )


    st.markdown(
        '<div class="section-title">'
        '📋 Histórico'
        '</div>',
        unsafe_allow_html=True,
    )


    if not logs.empty:

        st.dataframe(
            logs,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "Nenhuma execução registrada "
            "pela API."
        )


# ============================================================
# IA & INSIGHTS
# ============================================================

elif page == "IA & Insights":

    st.markdown(
        """
<div class="hero">

<h1>IA & Insights</h1>

<p>
Inteligência artificial aplicada à
análise operacional das ECVs.
</p>

</div>
""",
        unsafe_allow_html=True,
    )


    ecv_count = (
        len(ecvs_df)
        if not ecvs_df.empty
        else (
            perf["ecv"].nunique()
            if (
                not perf.empty
                and "ecv" in perf.columns
            )
            else 0
        )
    )


    a, b, c = st.columns(3)


    a.metric(
        "ECVs analisadas",
        number(ecv_count),
    )


    b.metric(
        "Vistorias analisadas",
        number(len(df)),
    )


    c.metric(
        "Copilot",
        "Ativo",
    )


    st.markdown(
        """
<div class="card">

<span class="badge">
ECV INTELLIGENCE AI
</span>

<h3>
Copilot operacional
</h3>

<div class="small">
A camada de IA utiliza os indicadores
operacionais para apoiar análise
e tomada de decisão.
</div>

</div>
""",
        unsafe_allow_html=True,
    )


    st.markdown(
        '<div class="section-title">'
        '💬 Copilot de Dados'
        '</div>',
        unsafe_allow_html=True,
    )


    question = st.text_input(
        "Pergunta",
        placeholder=(
            "Qual ECV teve melhor desempenho?"
        ),
    )


    st.caption(
        "Exemplos: Qual ECV teve melhor "
        "desempenho? • Qual teve pior "
        "desempenho? • Quantas vistorias existem?"
    )


    if st.button(
        "🔎 Consultar dados",
        type="primary",
    ):

        if not question.strip():

            st.warning(
                "Digite uma pergunta."
            )

        else:

            try:

                from services.ai_service import (
                    ask_data
                )


                with st.spinner(
                    "Analisando dados..."
                ):

                    answer = ask_data(
                        question,
                        df,
                    )


                st.markdown(
                    f"""
<div class="card">

<span class="badge">
COPILOT
</span>

<div style="margin-top:1rem">

{html.escape(
    str(answer)
)}

</div>

</div>
""",
                    unsafe_allow_html=True,
                )


            except Exception as exc:

                st.warning(
                    "O módulo de IA local "
                    "não está disponível."
                )


                st.caption(
                    f"Detalhes técnicos: {exc}"
                )


    if (
        not perf.empty
        and "taxa_aprovacao"
        in perf.columns
    ):

        perf_sorted = (
            perf
            .sort_values(
                "taxa_aprovacao",
                ascending=False,
            )
            .reset_index(drop=True)
        )


        best = perf_sorted.iloc[0]

        worst = perf_sorted.iloc[-1]


        x, y = st.columns(2)


        x.markdown(
            f"""
<div class="card">

<span class="badge">
OPORTUNIDADE
</span>

<h3>
{html.escape(
    str(
        best.get(
            "ecv",
            "N/D"
        )
    )
)}
</h3>

<div class="small">

Maior aprovação:

{safe_float(
    best.get(
        "taxa_aprovacao"
    )
):.1f}%

</div>

</div>
""",
            unsafe_allow_html=True,
        )


        y.markdown(
            f"""
<div class="card">

<span class="badge">
ATENÇÃO
</span>

<h3>
{html.escape(
    str(
        worst.get(
            "ecv",
            "N/D"
        )
    )
)}
</h3>

<div class="small">

Menor aprovação:

{safe_float(
    worst.get(
        "taxa_aprovacao"
    )
):.1f}%

</div>

</div>
""",
            unsafe_allow_html=True,
        )


# ============================================================
# ECVs
# ============================================================

elif page == "ECVs":

    st.markdown(
        """
<div class="hero">

<h1>ECVs</h1>

<p>
Visão consolidada de desempenho
por ECV.
</p>

</div>
""",
        unsafe_allow_html=True,
    )


    if ecvs_df.empty:

        st.info(
            "A API não retornou ECVs."
        )

    else:

        display_df = ecvs_df.copy()


        if (
            not perf.empty
            and "ecv" in perf.columns
            and "taxa_aprovacao"
            in perf.columns
        ):

            join_column = None


            if "nome" in display_df.columns:

                join_column = "nome"

            elif "ecv" in display_df.columns:

                join_column = "ecv"


            if join_column:

                performance_join = (
                    perf[
                        [
                            "ecv",
                            "taxa_aprovacao",
                        ]
                    ]
                    .copy()
                )


                display_df = (
                    display_df.merge(
                        performance_join,
                        left_on=join_column,
                        right_on="ecv",
                        how="left",
                    )
                )


                if join_column != "ecv":

                    display_df = (
                        display_df.drop(
                            columns=["ecv"],
                            errors="ignore",
                        )
                    )


        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# API & INTEGRAÇÕES
# ============================================================

elif page == "API":

    st.markdown(
        """
<div class="hero">

<h1>API & Integrações</h1>

<p>
Camada REST para integração com
sistemas externos, BI e parceiros.
</p>

</div>
""",
        unsafe_allow_html=True,
    )


    c1, c2, c3 = st.columns(3)


    c1.metric(
        "API",
        "Online"
        if api_online
        else "Offline",
    )


    c2.metric(
        "Versão",
        "3.0.0",
    )


    c3.metric(
        "Frontend",
        "3.1",
    )


    st.markdown(
        '<div class="section-title">'
        'Endpoints disponíveis'
        '</div>',
        unsafe_allow_html=True,
    )


    endpoints = [
        "GET /health",
        "GET /status",
        "GET /ecvs",
        "GET /ecvs/{ecv_id}",
        "GET /vistorias",
        "GET /indicadores",
        "GET /analytics/ecvs",
        "GET /analytics/quality",
        "GET /analytics/daily",
        "GET /dashboard",
        "GET /automations",
        "GET /powerbi/vistorias",
        "GET /powerbi/ecvs",
        "GET /powerbi/indicadores",
    ]


    for endpoint in endpoints:

        st.code(endpoint)


    st.markdown(
        '<div class="section-title">'
        '🔗 Documentação'
        '</div>',
        unsafe_allow_html=True,
    )


    st.link_button(
        "📚 Abrir Swagger / OpenAPI",
        f"{API_URL}/docs",
        use_container_width=True,
    )


    st.link_button(
        "❤️ Health Check",
        f"{API_URL}/health",
        use_container_width=True,
    )


    st.link_button(
        "📊 Status da API",
        f"{API_URL}/status",
        use_container_width=True,
    )


    st.markdown(
        '<div class="section-title">'
        '🏗️ Arquitetura'
        '</div>',
        unsafe_allow_html=True,
    )


    st.markdown(
        """
<div class="card">

<span class="badge">
SAAS ARCHITECTURE
</span>

<h3>
ECV Intelligence V3.1
</h3>

<div class="small">

Frontend<br>
→ Streamlit

<br><br>

Backend<br>
→ FastAPI

<br><br>

Analytics<br>
→ KPIs + Performance + Quality

<br><br>

IA<br>
→ Gemini / Copilot

<br><br>

Automação<br>
→ Automation Engine

<br><br>

BI<br>
→ Power BI API

</div>

</div>
""",
        unsafe_allow_html=True,
    )


    st.markdown(
        '<div class="section-title">'
        'Próxima evolução comercial'
        '</div>',
        unsafe_allow_html=True,
    )


    st.info(
        "Autenticação → organizações → usuários → "
        "organization_id → API Keys → limites de uso → "
        "planos SaaS → billing."
    )


# ============================================================
# RODAPÉ
# ============================================================

st.divider()


st.caption(
    f"ECV Intelligence V3.1 • "
    f"API {API_URL} • "
    f"Atualizado em "
    f"{datetime.now().strftime('%d/%m/%Y %H:%M')}"
)
