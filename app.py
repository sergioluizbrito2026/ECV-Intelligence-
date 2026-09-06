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
    os.getenv("ECV_API_TIMEOUT", "30")
)

# Limite de dados
MAX_VISTORIAS = int(
    os.getenv("ECV_MAX_VISTORIAS", "5000")
)

PAGE_SIZE = 50


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

.block-container{
    padding:1.5rem 2rem 2.5rem;
    max-width:100%!important;
}

#MainMenu,
footer{
    visibility:hidden;
}


/* SIDEBAR */

[data-testid="stSidebar"]{
    background:#0b1120;
    border-right:1px solid rgba(255,255,255,.08);
    min-width:270px!important;
    max-width:270px!important;
}

[data-testid="stSidebar"] *{
    color:#f8fafc;
}

.sidebar-brand{
    padding:8px 4px 18px 4px;
}

.sidebar-brand h2{
    margin:0;
    font-size:1.25rem;
    font-weight:750;
}

.sidebar-brand p{
    margin:5px 0 0;
    font-size:.76rem;
    color:#94a3b8;
}

.sidebar-section{
    margin-top:15px;
    margin-bottom:6px;
    padding-left:5px;
    font-size:.68rem;
    font-weight:800;
    letter-spacing:.10em;
    color:#64748b!important;
    text-transform:uppercase;
}

[data-testid="stSidebar"] .stButton{
    margin-bottom:3px;
}

[data-testid="stSidebar"] .stButton > button{
    width:100%;
    min-height:40px;
    border:1px solid transparent;
    border-radius:9px;
    background:transparent;
    color:#cbd5e1!important;
    text-align:left!important;
    font-size:.88rem;
    font-weight:500;
    padding:0 12px;
}

[data-testid="stSidebar"] .stButton > button:hover{
    background:#172033;
    border-color:rgba(255,255,255,.06);
    color:#ffffff!important;
}


/* HERO */

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


/* SECTION */

.section-title{
    font-size:1.1rem;
    font-weight:700;
    margin:1.2rem 0 .8rem;
}


/* METRICS */

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


/* CARDS */

.card{
    border:1px solid rgba(255,255,255,.08);
    border-radius:14px;
    padding:1.2rem 1.3rem;
    background:#1e293b;
    color:#f8fafc;
    margin-bottom:.8rem;
}

.card h3{
    margin:.65rem 0;
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


/* FILTERS */

.filter-box{
    border:1px solid rgba(255,255,255,.08);
    border-radius:14px;
    padding:1rem;
    background:#111827;
    margin-bottom:1rem;
}


/* FOOTER */

hr{
    border-color:rgba(255,255,255,.08)!important;
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


def first_existing_column(df, candidates):

    for column in candidates:

        if column in df.columns:
            return column

    return None


def clean_text(value):

    if pd.isna(value):
        return ""

    return str(value).strip()


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
            "limit": MAX_VISTORIAS
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
# NORMALIZAÇÃO VISTORIAS
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

    # -----------------------------------------
    # NORMALIZAÇÃO DOS NOMES
    # -----------------------------------------

    rename_map = {

        "date": "data_vistoria",
        "datetime": "data_vistoria",
        "created_at": "data_vistoria",

        "type": "tipo_vistoria",
        "tipo": "tipo_vistoria",

        "result": "resultado",
        "status": "resultado",

        "time": "tempo_minutos",
        "tempo": "tempo_minutos",

        "amount": "valor",
        "price": "valor",

        "ecv_nome": "ecv",
        "nome_ecv": "ecv",
        "empresa": "ecv",

        "city": "cidade",
        "municipio": "cidade",

        "plate": "placa",
        "vehicle_plate": "placa",

        "inspection_id": "id",
    }

    df = df.rename(
        columns={
            k: v
            for k, v in rename_map.items()
            if k in df.columns
        }
    )

    # -----------------------------------------
    # GARANTIR CAMPOS
    # -----------------------------------------

    expected_columns = [
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

    for column in expected_columns:

        if column not in df.columns:
            df[column] = ""

    # -----------------------------------------
    # DATA
    # -----------------------------------------

    df["data_dt"] = pd.to_datetime(
        df["data_vistoria"],
        errors="coerce",
    )

    # -----------------------------------------
    # TEXTO
    # -----------------------------------------

    for column in [
        "id",
        "ecv",
        "cidade",
        "placa",
        "tipo_vistoria",
        "resultado",
    ]:

        df[column] = (
            df[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    # -----------------------------------------
    # NUMÉRICOS
    # -----------------------------------------

    df["tempo_minutos"] = pd.to_numeric(
        df["tempo_minutos"],
        errors="coerce",
    )

    df["valor"] = pd.to_numeric(
        df["valor"],
        errors="coerce",
    )

    # -----------------------------------------
    # LIMITE
    # -----------------------------------------

    if len(df) > MAX_VISTORIAS:

        df = df.head(MAX_VISTORIAS)

    return df


# ============================================================
# OUTROS DATAFRAMES
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

<p>
Analytics, IA e automação para ECVs
</p>

</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# BLOCO 1
# ============================================================

st.sidebar.markdown(
    '<div class="sidebar-section">WORKSPACE</div>',
    unsafe_allow_html=True,
)

sidebar_button(
    "📊  Visão Geral",
    "Visão Geral",
)

sidebar_button(
    "🔎  Vistorias",
    "Vistorias",
)

sidebar_button(
    "🛡️  Qualidade",
    "Qualidade",
)


# ============================================================
# BLOCO 2
# ============================================================

st.sidebar.markdown(
    '<div class="sidebar-section">INTELIGÊNCIA</div>',
    unsafe_allow_html=True,
)

sidebar_button(
    "🤖  IA & Insights",
    "IA & Insights",
)


# ============================================================
# BLOCO 3
# ============================================================

st.sidebar.markdown(
    '<div class="sidebar-section">INTEGRAÇÕES</div>',
    unsafe_allow_html=True,
)

sidebar_button(
    "🔌  API",
    "API",
)

sidebar_button(
    "📈  Power BI",
    "Power BI",
)


# ============================================================
# BLOCO 4
# ============================================================

st.sidebar.markdown(
    '<div class="sidebar-section">GESTÃO</div>',
    unsafe_allow_html=True,
)

sidebar_button(
    "🏢  ECVs",
    "ECVs",
)

sidebar_button(
    "⚙️  Automações",
    "Automações",
)


# ============================================================
# BLOCO 5
# ============================================================

st.sidebar.markdown(
    '<div class="sidebar-section">SISTEMA</div>',
    unsafe_allow_html=True,
)

sidebar_button(
    "⚙️  Configurações",
    "Configurações",
)


# ============================================================
# ATUALIZAÇÃO
# ============================================================

st.sidebar.divider()

if st.sidebar.button(
    "🔄 Atualizar dados",
    use_container_width=True,
    key="refresh_data",
):

    st.cache_data.clear()
    st.rerun()


# ============================================================
# CARREGAMENTO INTELIGENTE
# ============================================================

page = st.session_state.page

health = get_api_health()

api_online = health.get(
    "ok",
    False,
)


# ============================================================
# SE API OFFLINE
# ============================================================

if not api_online:

    st.markdown(
        """
<div class="hero">

<h1>ECV Intelligence</h1>

<p>
Não foi possível conectar à API neste momento.
</p>

</div>
""",
        unsafe_allow_html=True,
    )

    st.error(
        "A API não respondeu corretamente."
    )

    st.link_button(
        "Abrir API",
        API_URL,
        use_container_width=True,
    )

    st.stop()


# ============================================================
# CARREGAR DADOS DE ACORDO COM A ABA
# ============================================================

dashboard_response = {
    "data": {}
}

indicadores_response = {
    "data": {}
}

vistorias_response = {
    "data": {}
}

ecvs_response = {
    "data": {}
}

performance_response = {
    "data": {}
}

quality_response = {
    "data": {}
}

daily_response = {
    "data": {}
}

automations_response = {
    "data": {}
}


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

dashboard_data = (
    dashboard_response.get("data")
    or {}
)

indicadores_data = (
    indicadores_response.get("data")
    or {}
)


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

    if (
        not daily.empty
        and "data" in daily.columns
        and "vistorias" in daily.columns
    ):

        daily["data"] = pd.to_datetime(
            daily["data"],
            errors="coerce",
        )

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
# VISTORIAS
# ============================================================

elif page == "Vistorias":

    st.markdown(
        """
<div class="hero">

<h1>Vistorias</h1>

<p>
Pesquisa, filtros e análise dos registros operacionais.
</p>

</div>
""",
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # API VAZIA
    # --------------------------------------------------------

    if df.empty:

        st.warning(
            "A API não retornou registros de vistoria."
        )

        st.info(
            "A tela está pronta para receber os dados "
            "assim que o endpoint /vistorias retornar registros."
        )

        st.code(
            f"GET {API_URL}/vistorias",
            language="text",
        )

    else:

        # ----------------------------------------------------
        # FILTROS
        # ----------------------------------------------------

        st.markdown(
            '<div class="section-title">'
            '🔎 Pesquisa e filtros'
            '</div>',
            unsafe_allow_html=True,
        )

        # BUSCA
        busca = st.text_input(
            "Pesquisar",
            placeholder="Digite placa ou ID da vistoria...",
            key="busca_vistoria",
        )

        c1, c2, c3 = st.columns(3)

        # ECV
        with c1:

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

        # CIDADE
        with c2:

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

        # TIPO
        with c3:

            type_values = sorted(
                [
                    x for x in
                    df["tipo_vistoria"].dropna().unique().tolist()
                    if str(x).strip()
                ]
            )

            type_filter = st.multiselect(
                "📋 Tipo",
                type_values,
                default=type_values,
                key="filtro_tipo",
            )

        c4, c5, c6 = st.columns(3)

        # RESULTADO
        with c4:

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

        # DATA
        with c5:

            valid_dates = (
                df["data_dt"]
                .dropna()
            )

            if not valid_dates.empty:

                min_date = valid_dates.min().date()
                max_date = valid_dates.max().date()

                date_filter = st.date_input(
                    "📅 Período",
                    value=(
                        min_date,
                        max_date,
                    ),
                    min_value=min_date,
                    max_value=max_date,
                    key="filtro_periodo",
                )

            else:

                date_filter = None

                st.caption(
                    "Período indisponível"
                )

        # LIMITE
        with c6:

            display_limit = st.selectbox(
                "📊 Registros exibidos",
                [
                    25,
                    50,
                    100,
                    250,
                    500,
                ],
                index=1,
                key="limite_tabela",
            )

        # ----------------------------------------------------
        # APLICAR FILTROS
        # ----------------------------------------------------

        filtered = df.copy()

        # Busca placa / ID
        if busca.strip():

            q = busca.strip().lower()

            mask = (
                filtered["placa"]
                .astype(str)
                .str.lower()
                .str.contains(
                    q,
                    na=False,
                )
            )

            mask |= (
                filtered["id"]
                .astype(str)
                .str.lower()
                .str.contains(
                    q,
                    na=False,
                )
            )

            filtered = filtered[mask]

        # ECV
        if ecv_filter != "Todas":

            filtered = filtered[
                filtered["ecv"]
                == ecv_filter
            ]

        # Cidade
        if city_filter != "Todas":

            filtered = filtered[
                filtered["cidade"]
                == city_filter
            ]

        # Tipo
        if type_values:

            filtered = filtered[
                filtered["tipo_vistoria"]
                .isin(type_filter)
            ]

        # Resultado
        if result_values:

            filtered = filtered[
                filtered["resultado"]
                .isin(result_filter)
            ]

        # Período
        if (
            date_filter
            and len(date_filter) == 2
        ):

            start_date = date_filter[0]
            end_date = date_filter[1]

            filtered = filtered[
                (
                    filtered["data_dt"]
                    .dt.date
                    >= start_date
                )
                &
                (
                    filtered["data_dt"]
                    .dt.date
                    <= end_date
                )
            ]

        # ----------------------------------------------------
        # KPIs
        # ----------------------------------------------------

        total_filtrado = len(filtered)

        resultados_lower = (
            filtered["resultado"]
            .astype(str)
            .str.lower()
        )

        aprovados = int(
            resultados_lower
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
            resultados_lower
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

        faturamento_filtrado = (
            filtered["valor"]
            .fillna(0)
            .sum()
        )

        k1, k2, k3, k4 = st.columns(4)

        k1.metric(
            "Registros",
            number(total_filtrado),
        )

        k2.metric(
            "Aprovação",
            (
                f"{aprovados / total_filtrado * 100:.1f}%"
                if total_filtrado
                else "0,0%"
            ),
        )

        k3.metric(
            "Reprovação",
            (
                f"{reprovados / total_filtrado * 100:.1f}%"
                if total_filtrado
                else "0,0%"
            ),
        )

        k4.metric(
            "Faturamento",
            money(
                faturamento_filtrado
            ),
        )

        # ----------------------------------------------------
        # EXPORTAÇÃO
        # ----------------------------------------------------

        st.markdown(
            '<div class="section-title">'
            '📋 Resultado da pesquisa'
            '</div>',
            unsafe_allow_html=True,
        )

        e1, e2 = st.columns([1, 4])

        with e1:

            csv_data = filtered.to_csv(
                index=False
            ).encode("utf-8-sig")

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

        # ----------------------------------------------------
        # TABELA
        # ----------------------------------------------------

        preferred_columns = [
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

        table_columns = [
            column
            for column in preferred_columns
            if column in filtered.columns
        ]

        table_df = filtered[
            table_columns
        ].copy()

        # Formatação
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

        # Limite visual
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

    quality_response = get_api_quality()

    quality_data = (
        quality_response.get("data")
        or {}
    )

    if not isinstance(
        quality_data,
        dict,
    ):

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
        '<div class="section-title">'
        '💬 Copilot de Dados'
        '</div>',
        unsafe_allow_html=True,
    )

    question = st.text_input(
        "Pergunta",
        placeholder="Qual ECV teve melhor desempenho?",
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

<span class="badge">
COPILOT
</span>

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
        '<div class="section-title">'
        'Endpoints'
        '</div>',
        unsafe_allow_html=True,
    )

    endpoints = [
        "GET /health",
        "GET /dashboard",
        "GET /indicadores",
        "GET /ecvs",
        "GET /vistorias",
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

    c1, c2 = st.columns(2)

    with c1:

        st.checkbox(
            "Atualização automática",
            value=True,
        )

        st.checkbox(
            "Mostrar gráficos avançados",
            value=True,
        )

    with c2:

        st.checkbox(
            "Ativar sugestões da IA",
            value=True,
        )

        st.checkbox(
            "Modo compacto",
            value=False,
        )

    if st.button(
        "💾 Salvar preferências",
        type="primary",
    ):

        st.success(
            "Preferências salvas."
        )


# ============================================================
# RODAPÉ
# ============================================================

st.divider()

st.caption(
    "ECV Intelligence • Analytics, IA e Automação"
)
