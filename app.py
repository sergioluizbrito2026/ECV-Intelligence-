
import html
import os
from datetime import datetime, date

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
    "https://ecv-intelligence-api-v3.onrender.com",
).rstrip("/")

API_TIMEOUT = int(
    os.getenv(
        "ECV_API_TIMEOUT",
        "30",
    )
)

MAX_VISTORIAS = int(
    os.getenv(
        "ECV_MAX_VISTORIAS",
        "5000",
    )
)

if MAX_VISTORIAS < 100:
    MAX_VISTORIAS = 100

PAGE_SIZE = 50


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
<style>

.stApp {
    background: #0f172a;
    color: #f8fafc;
}

.block-container {
    padding: 1.5rem 2rem 2.5rem;
    max-width: 100% !important;
}

#MainMenu,
footer {
    visibility: hidden;
}

[data-testid="stSidebar"] {
    background: #0b1120;
    border-right: 1px solid rgba(255,255,255,.08);
    min-width: 270px !important;
    max-width: 270px !important;
}

[data-testid="stSidebar"] * {
    color: #f8fafc;
}

.sidebar-brand {
    padding: 8px 4px 18px;
}

.sidebar-brand h2 {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 750;
}

.sidebar-brand p {
    margin: 5px 0 0;
    font-size: .76rem;
    color: #94a3b8;
}

.sidebar-section {
    margin-top: 15px;
    margin-bottom: 6px;
    padding-left: 5px;
    font-size: .68rem;
    font-weight: 800;
    letter-spacing: .10em;
    color: #64748b !important;
    text-transform: uppercase;
}

[data-testid="stSidebar"] .stButton {
    margin-bottom: 3px;
}

[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    min-height: 40px;
    border: 1px solid transparent;
    border-radius: 9px;
    background: transparent;
    color: #cbd5e1 !important;
    text-align: left !important;
    font-size: .88rem;
    font-weight: 500;
    padding: 0 12px;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background: #172033;
    border-color: rgba(255,255,255,.06);
    color: #ffffff !important;
}

.hero {
    padding: 1.5rem 1.8rem;
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 16px;
    background: #1e293b;
    margin-bottom: 1.2rem;
}

.hero h1 {
    margin: 0;
    font-size: 2rem;
    color: #f8fafc;
}

.hero p {
    margin: .45rem 0 0;
    color: #94a3b8;
}

.section-title {
    font-size: 1.1rem;
    font-weight: 700;
    margin: 1.2rem 0 .8rem;
}

[data-testid="stMetric"] {
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 14px;
    padding: 14px 16px;
    background: #1e293b;
}

[data-testid="stMetric"] label {
    color: #94a3b8 !important;
}

[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #f8fafc !important;
}

.card {
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 14px;
    padding: 1.2rem 1.3rem;
    background: #1e293b;
    color: #f8fafc;
    margin-bottom: .8rem;
}

.card h3 {
    margin: .65rem 0;
}

.badge {
    display: inline-block;
    padding: .22rem .55rem;
    border-radius: 999px;
    font-size: .72rem;
    font-weight: 700;
    background: #334155;
}

.small {
    font-size: .82rem;
    color: #94a3b8;
}

.data-limit {
    padding: .7rem .9rem;
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 10px;
    background: #111827;
    color: #94a3b8;
    font-size: .8rem;
    margin-bottom: 1rem;
}

.kpi-subtitle {
    color: #64748b;
    font-size: .72rem;
}

hr {
    border-color: rgba(255,255,255,.08) !important;
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


def safe_int(value, default=0):
    try:
        return int(float(value))
    except Exception:
        return default


def normalize_list_response(data, possible_keys=None):

    if isinstance(data, list):
        return data

    if isinstance(data, dict):

        keys = possible_keys or [
            "data",
            "items",
            "results",
            "records",
            "vistorias",
            "ecvs",
            "daily",
            "performance",
            "logs",
            "automations",
        ]

        for key in keys:

            value = data.get(key)

            if isinstance(value, list):
                return value

    return []


# ============================================================
# NAVEGAÇÃO
# ============================================================

if "page" not in st.session_state:
    st.session_state.page = "Visão Geral"


def navigate(page_name):
    st.session_state.page = page_name


def sidebar_button(label, page_name):

    clicked = st.sidebar.button(
        label,
        key=f"sidebar_{page_name}",
        use_container_width=True,
    )

    if clicked:
        navigate(page_name)
        st.rerun()


# ============================================================
# API CLIENT
# ============================================================

@st.cache_data(
    ttl=60,
    show_spinner=False,
)
def api_get(endpoint, params=None):

    url = f"{API_URL}{endpoint}"

    try:

        response = requests.get(
            url,
            params=params,
            timeout=API_TIMEOUT,
            headers={
                "Accept": "application/json",
                "User-Agent": "ECV-Intelligence-Streamlit/3.1",
            },
        )

        response.raise_for_status()

        try:
            data = response.json()
        except Exception:
            data = {}

        return {
            "ok": True,
            "status_code": response.status_code,
            "data": data,
            "error": None,
        }

    except requests.exceptions.Timeout:

        return {
            "ok": False,
            "status_code": None,
            "data": None,
            "error": "Tempo limite excedido.",
        }

    except requests.exceptions.ConnectionError:

        return {
            "ok": False,
            "status_code": None,
            "data": None,
            "error": "Não foi possível conectar à API.",
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
            "error": f"Erro HTTP: {exc}",
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


def get_api_dashboard():
    return api_get("/dashboard")


def get_api_indicadores():
    return api_get("/indicadores")


def get_api_vistorias():

    return api_get(
        "/vistorias",
        {
            "limit": MAX_VISTORIAS,
        },
    )


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
# DATAFRAME — VISTORIAS
# ============================================================

def build_vistorias_dataframe(data):

    records = normalize_list_response(
        data,
        [
            "data",
            "vistorias",
            "items",
            "results",
            "records",
        ],
    )

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)

    rename_map = {

        "id": "id",
        "inspection_id": "id",

        "ecv_id": "ecv_id",

        "data_hora": "data_vistoria",
        "data": "data_vistoria",
        "date": "data_vistoria",
        "datetime": "data_vistoria",
        "created_at": "data_vistoria",

        "ecv": "ecv",
        "ecv_nome": "ecv",
        "nome_ecv": "ecv",
        "empresa": "ecv",

        "cidade": "cidade",
        "city": "cidade",
        "municipio": "cidade",

        "estado": "estado",
        "uf": "estado",

        "placa": "placa",
        "plate": "placa",
        "vehicle_plate": "placa",

        "tipo": "tipo_vistoria",
        "type": "tipo_vistoria",
        "tipo_vistoria": "tipo_vistoria",

        "resultado": "resultado",
        "result": "resultado",
        "status": "resultado",

        "tempo": "tempo_minutos",
        "time": "tempo_minutos",
        "tempo_minutos": "tempo_minutos",

        "valor": "valor",
        "amount": "valor",
        "price": "valor",
    }

    df = df.rename(
        columns={
            column: rename_map[column]
            for column in df.columns
            if column in rename_map
        }
    )

    expected_columns = [
        "id",
        "ecv_id",
        "data_vistoria",
        "ecv",
        "cidade",
        "estado",
        "placa",
        "tipo_vistoria",
        "resultado",
        "tempo_minutos",
        "valor",
    ]

    for column in expected_columns:

        if column not in df.columns:
            df[column] = ""

    df["data_dt"] = pd.to_datetime(
        df["data_vistoria"],
        errors="coerce",
    )

    text_columns = [
        "id",
        "ecv_id",
        "ecv",
        "cidade",
        "estado",
        "placa",
        "tipo_vistoria",
        "resultado",
    ]

    for column in text_columns:

        df[column] = (
            df[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    df["tempo_minutos"] = pd.to_numeric(
        df["tempo_minutos"],
        errors="coerce",
    )

    df["valor"] = pd.to_numeric(
        df["valor"],
        errors="coerce",
    )

    if len(df) > MAX_VISTORIAS:
        df = df.head(MAX_VISTORIAS)

    return df


# ============================================================
# DATAFRAME — ECV
# ============================================================

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


# ============================================================
# DATAFRAME — DAILY
# ============================================================

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

    df = df.rename(
        columns={
            "date": "data",
            "total": "vistorias",
            "count": "vistorias",
        }
    )

    if "data" in df.columns:

        df["data"] = pd.to_datetime(
            df["data"],
            errors="coerce",
        )

    if "vistorias" in df.columns:

        df["vistorias"] = pd.to_numeric(
            df["vistorias"],
            errors="coerce",
        ).fillna(0)

    return df


# ============================================================
# DATAFRAME — PERFORMANCE
# ============================================================

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

    df = df.rename(
        columns={
            "nome": "ecv",
            "ecv_nome": "ecv",
            "approval_rate": "taxa_aprovacao",
            "taxa_aprovacao_percentual": "taxa_aprovacao",
        }
    )

    if "taxa_aprovacao" in df.columns:

        df["taxa_aprovacao"] = pd.to_numeric(
            df["taxa_aprovacao"],
            errors="coerce",
        ).fillna(0)

    return df


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown(
    """
<div class="sidebar-brand">
<h2>📊 ECV Intelligence</h2>
<p>Analytics, IA e automação para ECVs</p>
</div>
""",
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    '<div class="sidebar-section">WORKSPACE</div>',
    unsafe_allow_html=True,
)

sidebar_button("📊  Visão Geral", "Visão Geral")
sidebar_button("🔎  Vistorias", "Vistorias")
sidebar_button("🛡️  Qualidade", "Qualidade")

st.sidebar.markdown(
    '<div class="sidebar-section">INTELIGÊNCIA</div>',
    unsafe_allow_html=True,
)

sidebar_button("🤖  IA & Insights", "IA & Insights")

st.sidebar.markdown(
    '<div class="sidebar-section">INTEGRAÇÕES</div>',
    unsafe_allow_html=True,
)

sidebar_button("🔌  API", "API")
sidebar_button("📈  Power BI", "Power BI")

st.sidebar.markdown(
    '<div class="sidebar-section">GESTÃO</div>',
    unsafe_allow_html=True,
)

sidebar_button("🏢  ECVs", "ECVs")
sidebar_button("⚙️  Automações", "Automações")

st.sidebar.markdown(
    '<div class="sidebar-section">SISTEMA</div>',
    unsafe_allow_html=True,
)

sidebar_button("⚙️  Configurações", "Configurações")

st.sidebar.divider()

st.sidebar.caption("Limite de dados")

st.sidebar.metric(
    "Vistorias máximas",
    number(MAX_VISTORIAS),
)

st.sidebar.caption(
    f"A API será consultada com limite de "
    f"{number(MAX_VISTORIAS)} registros."
)

if st.sidebar.button(
    "🔄 Atualizar dados",
    use_container_width=True,
    key="refresh_data",
):

    st.cache_data.clear()
    st.rerun()


# ============================================================
# HEALTH
# ============================================================

page = st.session_state.page

health = get_api_health()

api_online = health.get(
    "ok",
    False,
)

if not api_online:

    st.markdown(
        """
<div class="hero">
<h1>ECV Intelligence</h1>
<p>Não foi possível conectar à API neste momento.</p>
</div>
""",
        unsafe_allow_html=True,
    )

    st.error("A API não respondeu corretamente.")

    error_message = health.get("error")

    if error_message:
        st.caption(error_message)

    st.link_button(
        "Abrir API",
        API_URL,
        use_container_width=True,
    )

    st.stop()


# ============================================================
# RESPOSTAS
# ============================================================

dashboard_response = {"data": {}}
indicadores_response = {"data": {}}
vistorias_response = {"data": {}}
ecvs_response = {"data": {}}
performance_response = {"data": {}}
quality_response = {"data": {}}
daily_response = {"data": {}}
automations_response = {"data": {}}


# ============================================================
# CARREGAMENTO
# ============================================================

if page == "Visão Geral":

    dashboard_response = get_api_dashboard()
    indicadores_response = get_api_indicadores()
    performance_response = get_api_analytics_ecvs()
    daily_response = get_api_daily()

elif page == "Vistorias":

    vistorias_response = get_api_vistorias()

elif page == "Qualidade":

    quality_response = get_api_quality()

elif page == "IA & Insights":

    vistorias_response = get_api_vistorias()
    ecvs_response = get_api_ecvs()
    performance_response = get_api_analytics_ecvs()

elif page == "ECVs":

    ecvs_response = get_api_ecvs()
    performance_response = get_api_analytics_ecvs()

elif page == "Automações":

    automations_response = get_api_automations()


# ============================================================
# DATAFRAMES
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
# KPI
# ============================================================

dashboard_data = dashboard_response.get("data") or {}
indicadores_data = indicadores_response.get("data") or {}


def extract_kpi(keys, default=0):

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

    st.markdown(
        f"""
<div class="data-limit">
📊 Base operacional carregada com limite de
<strong>{number(MAX_VISTORIAS)}</strong> vistorias.
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
        '<div class="section-title">Performance operacional</div>',
        unsafe_allow_html=True,
    )

    a, b = st.columns(2)

    if (
        not daily.empty
        and "data" in daily.columns
        and "vistorias" in daily.columns
    ):

        fig1 = px.line(
            daily,
            x="data",
            y="vistorias",
            markers=True,
            title="Volume diário de vistorias",
        )

        fig1.update_layout(
            plot_bgcolor="#1e293b",
            paper_bgcolor="#1e293b",
            font=dict(color="#94a3b8"),
        )

        a.plotly_chart(
            fig1,
            use_container_width=True,
        )

    else:

        a.info(
            "Não existem dados suficientes para o gráfico diário."
        )

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
            title="Taxa de aprovação por ECV (%)",
        )

        fig2.update_layout(
            plot_bgcolor="#1e293b",
            paper_bgcolor="#1e293b",
            font=dict(color="#94a3b8"),
            showlegend=False,
        )

        b.plotly_chart(
            fig2,
            use_container_width=True,
        )

    else:

        b.info(
            "Não existem dados de performance das ECVs."
        )


# ============================================================
# VISTORIAS — VERSÃO PROFISSIONAL
# ============================================================

elif page == "Vistorias":

    st.markdown(
        """
<div class="hero">
<h1>🚗 Vistorias</h1>
<p>
Monitoramento operacional, filtros avançados e análise
detalhada das inspeções realizadas.
</p>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
<div class="data-limit">
📦 Consulta atual limitada a
<strong>{number(MAX_VISTORIAS)}</strong> registros.
</div>
""",
        unsafe_allow_html=True,
    )

    if df.empty:

        st.warning(
            "A API não retornou registros de vistoria."
        )

        st.code(
            f"GET {API_URL}/vistorias?limit={MAX_VISTORIAS}",
            language="text",
        )

    else:

        # ====================================================
        # FILTROS
        # ====================================================

        st.markdown(
            '<div class="section-title">🔎 Filtros de pesquisa</div>',
            unsafe_allow_html=True,
        )

        f1, f2, f3, f4 = st.columns(4)

        with f1:

            busca = st.text_input(
                "Pesquisar",
                placeholder="Placa ou ID...",
                key="busca_vistoria",
            )

        with f2:

            ecv_values = sorted(
                [
                    x for x in
                    df["ecv"].dropna().unique().tolist()
                    if str(x).strip()
                ]
            )

            ecv_filter = st.selectbox(
                "🏢 ECV",
                ["Todas"] + ecv_values,
                key="filtro_ecv",
            )

        with f3:

            city_values = sorted(
                [
                    x for x in
                    df["cidade"].dropna().unique().tolist()
                    if str(x).strip()
                ]
            )

            city_filter = st.selectbox(
                "📍 Cidade",
                ["Todas"] + city_values,
                key="filtro_cidade",
            )

        with f4:

            state_values = sorted(
                [
                    x for x in
                    df["estado"].dropna().unique().tolist()
                    if str(x).strip()
                ]
            )

            state_filter = st.selectbox(
                "🗺️ Estado",
                ["Todos"] + state_values,
                key="filtro_estado",
            )

        f5, f6, f7, f8 = st.columns(4)

        with f5:

            type_values = sorted(
                [
                    x for x in
                    df["tipo_vistoria"].dropna().unique().tolist()
                    if str(x).strip()
                ]
            )

            type_filter = st.multiselect(
                "📋 Tipo de vistoria",
                type_values,
                default=type_values,
                key="filtro_tipo",
            )

        with f6:

            result_values = sorted(
                [
                    x for x in
                    df["resultado"].dropna().unique().tolist()
                    if str(x).strip()
                ]
            )

            result_filter = st.multiselect(
                "🎯 Resultado",
                result_values,
                default=result_values,
                key="filtro_resultado",
            )

        with f7:

            valid_dates = df["data_dt"].dropna()

            if not valid_dates.empty:

                min_date = valid_dates.min().date()
                max_date = valid_dates.max().date()

                date_filter = st.date_input(
                    "📅 Período",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date,
                    key="filtro_periodo",
                )

            else:

                date_filter = None

        with f8:

            display_limit = st.selectbox(
                "📊 Registros exibidos",
                [25, 50, 100, 250, 500],
                index=1,
                key="limite_tabela",
            )

        # ====================================================
        # APLICAÇÃO DOS FILTROS
        # ====================================================

        filtered = df.copy()

        if busca.strip():

            q = busca.strip().lower()

            mask = (
                filtered["placa"]
                .astype(str)
                .str.lower()
                .str.contains(
                    q,
                    na=False,
                    regex=False,
                )
            )

            mask |= (
                filtered["id"]
                .astype(str)
                .str.lower()
                .str.contains(
                    q,
                    na=False,
                    regex=False,
                )
            )

            filtered = filtered[mask]

        if ecv_filter != "Todas":

            filtered = filtered[
                filtered["ecv"] == ecv_filter
            ]

        if city_filter != "Todas":

            filtered = filtered[
                filtered["cidade"] == city_filter
            ]

        if state_filter != "Todos":

            filtered = filtered[
                filtered["estado"] == state_filter
            ]

        if type_filter:

            filtered = filtered[
                filtered["tipo_vistoria"].isin(type_filter)
            ]

        if result_filter:

            filtered = filtered[
                filtered["resultado"].isin(result_filter)
            ]

        if (
            date_filter
            and isinstance(date_filter, tuple)
            and len(date_filter) == 2
        ):

            start_date = date_filter[0]
            end_date = date_filter[1]

            filtered = filtered[
                (
                    filtered["data_dt"].dt.date
                    >= start_date
                )
                &
                (
                    filtered["data_dt"].dt.date
                    <= end_date
                )
            ]

        # ====================================================
        # KPIs
        # ====================================================

        total_filtrado = len(filtered)

        resultado_normalizado = (
            filtered["resultado"]
            .astype(str)
            .str.lower()
            .str.strip()
        )

        aprovados = int(
            resultado_normalizado
            .isin(
                [
                    "aprovado",
                    "aprovada",
                    "aprovados",
                    "aprovadas",
                ]
            )
            .sum()
        )

        reprovados = int(
            resultado_normalizado
            .isin(
                [
                    "reprovado",
                    "reprovada",
                    "reprovados",
                    "reprovadas",
                ]
            )
            .sum()
        )

        taxa_aprovacao_filtro = (
            aprovados / total_filtrado * 100
            if total_filtrado
            else 0
        )

        taxa_reprovacao_filtro = (
            reprovados / total_filtrado * 100
            if total_filtrado
            else 0
        )

        tempo_medio_filtro = (
            filtered["tempo_minutos"]
            .mean()
            if not filtered.empty
            else 0
        )

        faturamento_filtrado = (
            filtered["valor"]
            .fillna(0)
            .sum()
        )

        st.markdown(
            '<div class="section-title">📊 Indicadores filtrados</div>',
            unsafe_allow_html=True,
        )

        k1, k2, k3, k4, k5, k6 = st.columns(6)

        k1.metric(
            "Vistorias",
            number(total_filtrado),
        )

        k2.metric(
            "Aprovadas",
            number(aprovados),
        )

        k3.metric(
            "Reprovadas",
            number(reprovados),
        )

        k4.metric(
            "Taxa aprovação",
            f"{taxa_aprovacao_filtro:.1f}%",
        )

        k5.metric(
            "Tempo médio",
            f"{safe_float(tempo_medio_filtro):.1f} min",
        )

        k6.metric(
            "Faturamento",
            money(faturamento_filtrado),
        )

        # ====================================================
        # GRÁFICOS
        # ====================================================

        if not filtered.empty:

            st.markdown(
                '<div class="section-title">📈 Análise operacional</div>',
                unsafe_allow_html=True,
            )

            g1, g2 = st.columns(2)

            # -----------------------------------------------
            # RESULTADOS
            # -----------------------------------------------

            result_chart = (
                filtered["resultado"]
                .value_counts()
                .reset_index()
            )

            result_chart.columns = [
                "resultado",
                "quantidade",
            ]

            fig_result = px.pie(
                result_chart,
                names="resultado",
                values="quantidade",
                hole=.55,
                title="Distribuição dos resultados",
            )

            fig_result.update_layout(
                plot_bgcolor="#1e293b",
                paper_bgcolor="#1e293b",
                font=dict(color="#94a3b8"),
            )

            g1.plotly_chart(
                fig_result,
                use_container_width=True,
            )

            # -----------------------------------------------
            # TIPOS
            # -----------------------------------------------

            type_chart = (
                filtered["tipo_vistoria"]
                .value_counts()
                .reset_index()
            )

            type_chart.columns = [
                "tipo_vistoria",
                "quantidade",
            ]

            fig_type = px.bar(
                type_chart,
                x="tipo_vistoria",
                y="quantidade",
                text_auto=True,
                title="Vistorias por tipo",
            )

            fig_type.update_layout(
                plot_bgcolor="#1e293b",
                paper_bgcolor="#1e293b",
                font=dict(color="#94a3b8"),
                showlegend=False,
            )

            g2.plotly_chart(
                fig_type,
                use_container_width=True,
            )

            # -----------------------------------------------
            # PERFORMANCE ECV
            # -----------------------------------------------

            ecv_analysis = (
                filtered
                .groupby("ecv")
                .agg(
                    vistorias=("id", "count"),
                    tempo_medio=("tempo_minutos", "mean"),
                    faturamento=("valor", "sum"),
                )
                .reset_index()
                .sort_values(
                    "vistorias",
                    ascending=False,
                )
            )

            if not ecv_analysis.empty:

                st.markdown(
                    '<div class="section-title">🏢 Performance por ECV</div>',
                    unsafe_allow_html=True,
                )

                fig_ecv = px.bar(
                    ecv_analysis,
                    x="ecv",
                    y="vistorias",
                    text_auto=True,
                    title="Volume de vistorias por ECV",
                )

                fig_ecv.update_layout(
                    plot_bgcolor="#1e293b",
                    paper_bgcolor="#1e293b",
                    font=dict(color="#94a3b8"),
                    showlegend=False,
                )

                st.plotly_chart(
                    fig_ecv,
                    use_container_width=True,
                )

        # ====================================================
        # EXPORTAÇÃO
        # ====================================================

        st.markdown(
            '<div class="section-title">📋 Resultado da pesquisa</div>',
            unsafe_allow_html=True,
        )

        e1, e2 = st.columns([1, 4])

        with e1:

            export_df = filtered.copy()

            if "data_dt" in export_df.columns:
                export_df = export_df.drop(
                    columns=["data_dt"]
                )

            csv_data = (
                export_df
                .to_csv(
                    index=False
                )
                .encode("utf-8-sig")
            )

            st.download_button(
                "📥 Exportar CSV",
                csv_data,
                "vistorias_filtradas.csv",
                "text/csv",
                use_container_width=True,
            )

        with e2:

            st.caption(
                f"Encontrados {number(total_filtrado)} registros."
            )

        # ====================================================
        # TABELA
        # ====================================================

        preferred_columns = [
            "id",
            "ecv_id",
            "data_vistoria",
            "ecv",
            "cidade",
            "estado",
            "placa",
            "tipo_vistoria",
            "resultado",
            "tempo_minutos",
            "valor",
        ]

        table_columns = [
            column
            for column in preferred_columns
            if column in filtered.columns
        ]

        table_df = filtered[
            table_columns
        ].copy()

        if "data_vistoria" in table_df.columns:

            table_df["data_vistoria"] = (
                pd.to_datetime(
                    table_df["data_vistoria"],
                    errors="coerce",
                )
                .dt.strftime(
                    "%d/%m/%Y %H:%M"
                )
            )

        if "valor" in table_df.columns:

            table_df["valor"] = (
                table_df["valor"]
                .apply(money)
            )

        if "tempo_minutos" in table_df.columns:

            table_df["tempo_minutos"] = (
                table_df["tempo_minutos"]
                .round(1)
            )

        table_df = table_df.head(
            display_limit
        )

        st.dataframe(
            table_df,
            use_container_width=True,
            hide_index=True,
            height=560,
        )

        if total_filtrado > display_limit:

            st.info(
                f"Exibindo os primeiros "
                f"{number(display_limit)} registros "
                f"de {number(total_filtrado)} encontrados. "
                f"O CSV contém todos os registros filtrados."
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
Diagnóstico da confiabilidade da base operacional.
</p>
</div>
""",
        unsafe_allow_html=True,
    )

    quality_data = quality_response.get("data") or {}

    if not isinstance(quality_data, dict):

        st.info(
            "A API não retornou informações de qualidade."
        )

    else:

        total = quality_data.get(
            "total",
            quality_data.get(
                "registros",
                0,
            ),
        )

        duplicados = quality_data.get(
            "duplicados",
            0,
        )

        nulos = quality_data.get(
            "nulos",
            quality_data.get(
                "campos_vazios",
                0,
            ),
        )

        placas_invalidas = quality_data.get(
            "placas_invalidas",
            0,
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


# ============================================================
# IA & INSIGHTS
# ============================================================

elif page == "IA & Insights":

    st.markdown(
        """
<div class="hero">
<h1>IA & Insights</h1>
<p>
Inteligência artificial aplicada aos dados operacionais.
</p>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
<div class="data-limit">
🤖 O Copilot está analisando até
<strong>{number(MAX_VISTORIAS)}</strong>
vistorias carregadas da base.
</div>
""",
        unsafe_allow_html=True,
    )

    ecv_count = (
        len(ecvs_df)
        if not ecvs_df.empty
        else 0
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
        '<div class="section-title">💬 Copilot de Dados</div>',
        unsafe_allow_html=True,
    )

    question = st.text_input(
        "Pergunta",
        placeholder="Qual ECV teve melhor desempenho?",
        key="copilot_question",
    )

    if st.button(
        "🔎 Consultar dados",
        type="primary",
        key="consultar_copilot",
    ):

        if not question.strip():

            st.warning(
                "Digite uma pergunta."
            )

        elif df.empty:

            st.warning(
                "Não existem dados de vistorias disponíveis."
            )

        else:

            try:

                from services.ai_service import ask_data

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
<span class="badge">COPILOT</span>
<div style="margin-top:1rem">
{html.escape(str(answer))}
</div>
</div>
""",
                    unsafe_allow_html=True,
                )

            except Exception as exc:

                st.error(
                    "Não foi possível executar o Copilot."
                )

                st.caption(
                    f"Detalhes: {exc}"
                )


# ============================================================
# ECVs
# ============================================================

elif page == "ECVs":

    st.markdown(
        """
<div class="hero">
<h1>Gestão de ECVs</h1>
<p>
Visão consolidada das Empresas Credenciadas de Vistoria.
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

        st.metric(
            "ECVs cadastradas",
            number(len(ecvs_df)),
        )

        st.dataframe(
            ecvs_df,
            use_container_width=True,
            hide_index=True,
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
Monitoramento das regras e execuções automatizadas.
</p>
</div>
""",
        unsafe_allow_html=True,
    )

    automation_data = (
        automations_response.get("data")
        if automations_response.get("ok")
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

    if logs.empty:

        st.info(
            "Nenhuma execução registrada pela API."
        )

    else:

        st.metric(
            "Execuções",
            number(len(logs)),
        )

        st.dataframe(
            logs,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# API
# ============================================================

elif page == "API":

    st.markdown(
        """
<div class="hero">
<h1>API & Integrações</h1>
<p>
Camada REST para integração com sistemas externos,
BI e parceiros.
</p>
</div>
""",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Status",
        "Online",
    )

    c2.metric(
        "Health",
        "OK",
    )

    c3.metric(
        "API",
        "REST",
    )

    st.markdown(
        '<div class="section-title">Endpoints</div>',
        unsafe_allow_html=True,
    )

    endpoints = [
        "GET /health",
        "GET /dashboard",
        "GET /indicadores",
        "GET /ecvs",
        f"GET /vistorias?limit={MAX_VISTORIAS}",
        "GET /analytics/ecvs",
        "GET /analytics/quality",
        "GET /analytics/daily",
        "GET /automations",
        "GET /powerbi/vistorias",
        "GET /powerbi/ecvs",
        "GET /powerbi/indicadores",
    ]

    for endpoint in endpoints:
        st.code(endpoint)

    st.markdown(
        '<div class="section-title">⚙️ Configuração de dados</div>',
        unsafe_allow_html=True,
    )

    st.info(
        f"""
O frontend está configurado para solicitar até
{number(MAX_VISTORIAS)} vistorias por consulta.

Para alterar o limite, defina:

ECV_MAX_VISTORIAS

Exemplo:

ECV_MAX_VISTORIAS=10000
"""
    )


# ============================================================
# POWER BI
# ============================================================

elif page == "Power BI":

    st.markdown(
        """
<div class="hero">
<h1>Power BI</h1>
<p>
Integração analítica para consumo dos dados da plataforma.
</p>
</div>
""",
        unsafe_allow_html=True,
    )

    a, b, c = st.columns(3)

    with a:

        st.markdown(
            """
<div class="card">
<h3>🚗 Vistorias</h3>
<div class="small">
Dados operacionais das vistorias.
</div>
</div>
""",
            unsafe_allow_html=True,
        )

        st.link_button(
            "Abrir endpoint",
            f"{API_URL}/powerbi/vistorias",
            use_container_width=True,
        )

    with b:

        st.markdown(
            """
<div class="card">
<h3>🏢 ECVs</h3>
<div class="small">
Dados consolidados das ECVs.
</div>
</div>
""",
            unsafe_allow_html=True,
        )

        st.link_button(
            "Abrir endpoint",
            f"{API_URL}/powerbi/ecvs",
            use_container_width=True,
        )

    with c:

        st.markdown(
            """
<div class="card">
<h3>📊 Indicadores</h3>
<div class="small">
KPIs preparados para análise.
</div>
</div>
""",
            unsafe_allow_html=True,
        )

        st.link_button(
            "Abrir endpoint",
            f"{API_URL}/powerbi/indicadores",
            use_container_width=True,
        )

    st.markdown(
        '<div class="section-title">📌 Integração</div>',
        unsafe_allow_html=True,
    )

    st.info(
        """
Os endpoints Power BI estão separados dos endpoints
operacionais para facilitar a integração do dashboard
com o Power BI.
"""
    )


# ============================================================
# CONFIGURAÇÕES
# ============================================================

elif page == "Configurações":

    st.markdown(
        """
<div class="hero">
<h1>Configurações</h1>
<p>
Preferências da plataforma ECV Intelligence.
</p>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
<div class="card">
<h3>📊 Limite de dados</h3>

<div class="small">

Limite atual de vistorias:
<strong>{number(MAX_VISTORIAS)}</strong>

<br><br>

Variável de ambiente:

<strong>ECV_MAX_VISTORIAS</strong>

<br><br>

Exemplo:

<strong>ECV_MAX_VISTORIAS=10000</strong>

</div>
</div>
""",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)

    with c1:

        st.checkbox(
            "Atualização automática",
            value=True,
            key="config_atualizacao",
        )

        st.checkbox(
            "Mostrar gráficos avançados",
            value=True,
            key="config_graficos",
        )

    with c2:

        st.checkbox(
            "Ativar sugestões da IA",
            value=True,
            key="config_ia",
        )

        st.checkbox(
            "Modo compacto",
            value=False,
            key="config_compacto",
        )

    if st.button(
        "💾 Salvar preferências",
        type="primary",
        key="salvar_config",
    ):

        st.success(
            "Preferências salvas."
        )


    
