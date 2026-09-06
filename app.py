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
    "https://ecv-intelligence-api-v3.onrender.com",
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

/* ========================================================
   APP
   ======================================================== */

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


/* ========================================================
   SIDEBAR
   ======================================================== */

[data-testid="stSidebar"]{
    background:#0b1120;
    border-right:1px solid rgba(255,255,255,.08);
    min-width:280px!important;
    max-width:280px!important;
}

[data-testid="stSidebar"] *{
    color:#f8fafc;
}

.sidebar-brand{
    padding:8px 4px 16px 4px;
}

.sidebar-brand h2{
    margin:0;
    font-size:1.25rem;
    font-weight:750;
    color:#f8fafc;
}

.sidebar-brand p{
    margin:5px 0 0;
    font-size:.76rem;
    color:#94a3b8;
    line-height:1.4;
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


/* ========================================================
   BOTÕES SIDEBAR
   ======================================================== */

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
    transition:all .15s ease;
}

[data-testid="stSidebar"] .stButton > button:hover{
    background:#172033;
    border-color:rgba(255,255,255,.06);
    color:#ffffff!important;
}

.sidebar-active > div > button{
    background:#1e293b!important;
    border-color:rgba(255,255,255,.10)!important;
    color:#ffffff!important;
    font-weight:700!important;
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
   SEÇÕES
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

.success{
    color:#4ade80;
}

.danger{
    color:#f87171;
}


/* ========================================================
   INTEGRAÇÕES
   ======================================================== */

.integration-card{
    border:1px solid rgba(255,255,255,.08);
    border-radius:14px;
    background:#1e293b;
    padding:1.3rem;
    min-height:150px;
}

.integration-card h3{
    margin:.4rem 0;
}

.integration-card p{
    color:#94a3b8;
    font-size:.84rem;
}


/* ========================================================
   TABELAS
   ======================================================== */

[data-testid="stDataFrame"]{
    border-radius:12px;
    overflow:hidden;
}


/* ========================================================
   DIVIDER
   ======================================================== */

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
            "ecvs",
            "vistorias",
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


# ============================================================
# CLIENTE DA API
# ============================================================

@st.cache_data(ttl=30, show_spinner=False)
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
            "error": "Tempo limite excedido ao consultar a API.",
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
            "error": f"Erro HTTP na API: {exc}",
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


def get_api_powerbi_vistorias():
    return api_get("/powerbi/vistorias")


def get_api_powerbi_ecvs():
    return api_get("/powerbi/ecvs")


def get_api_powerbi_indicadores():
    return api_get("/powerbi/indicadores")


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

    df = df.rename(columns=rename_map)

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

    return df.rename(columns=rename_map)


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
        "taxa_aprovacao_percentual": "taxa_aprovacao",
    }

    df = df.rename(columns=rename_map)

    if "taxa_aprovacao" in df.columns:

        df["taxa_aprovacao"] = pd.to_numeric(
            df["taxa_aprovacao"],
            errors="coerce",
        ).fillna(0)

    return df


# ============================================================
# CARREGAMENTO DA API
# ============================================================

with st.spinner("Carregando dados da ECV Intelligence..."):

    health = get_api_health()

    dashboard_response = get_api_dashboard()

    indicadores_response = get_api_indicadores()

    vistorias_response = get_api_vistorias()

    ecvs_response = get_api_ecvs()

    performance_response = get_api_analytics_ecvs()

    quality_response = get_api_quality()

    daily_response = get_api_daily()

    automations_response = get_api_automations()


api_online = health.get("ok", False)


# ============================================================
# SIDEBAR — 5 BLOCOS
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
# BLOCO 1 — WORKSPACE
# ============================================================

st.sidebar.markdown(
    '<div class="sidebar-section">WORKSPACE</div>',
    unsafe_allow_html=True,
)


def sidebar_button(label, page_name):

    active = (
        st.session_state.page == page_name
    )

    wrapper = (
        '<div class="sidebar-active">'
        if active
        else '<div>'
    )

    st.sidebar.markdown(
        wrapper,
        unsafe_allow_html=True,
    )

    clicked = st.sidebar.button(
        label,
        key=f"sidebar_{page_name}",
        use_container_width=True,
    )

    st.sidebar.markdown(
        "</div>",
        unsafe_allow_html=True,
    )

    if clicked:
        navigate(page_name)
        st.rerun()


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
# BLOCO 2 — INTELIGÊNCIA
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
# BLOCO 3 — INTEGRAÇÕES
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
# BLOCO 4 — GESTÃO
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
# BLOCO 5 — AMBIENTE / CONTA
# ============================================================

st.sidebar.markdown(
    '<div class="sidebar-section">AMBIENTE / CONTA</div>',
    unsafe_allow_html=True,
)

sidebar_button(
    "👤  Meu Perfil",
    "Meu Perfil",
)

sidebar_button(
    "⚙️  Configurações",
    "Configurações",
)


# ============================================================
# AÇÕES
# ============================================================

st.sidebar.divider()

if st.sidebar.button(
    "🔄  Atualizar dados",
    use_container_width=True,
    key="refresh_data",
):

    st.cache_data.clear()
    st.rerun()


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
# VERIFICAÇÃO API
# ============================================================

if not api_online:

    st.error(
        "A plataforma não conseguiu carregar os dados "
        "da API neste momento."
    )

    st.link_button(
        "Abrir serviço",
        API_URL,
        use_container_width=True,
    )

    st.stop()


# ============================================================
# KPI
# ============================================================

dashboard_data = (
    dashboard_response.get("data") or {}
)

indicadores_data = (
    indicadores_response.get("data") or {}
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

if st.session_state.page == "Visão Geral":

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

    if (
        not perf.empty
        and "taxa_aprovacao" in perf.columns
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

        x, y, z = st.columns(3)

        x.markdown(
            f"""
<div class="card">

<span class="badge">
MELHOR DESEMPENHO
</span>

<h3>
{html.escape(str(best.get("ecv", "N/D")))}
</h3>

<div class="success">
{safe_float(best.get("taxa_aprovacao")):.1f}%
de aprovação
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
{html.escape(str(worst.get("ecv", "N/D")))}
</h3>

<div class="danger">
{safe_float(worst.get("taxa_aprovacao")):.1f}%
de aprovação
</div>

</div>
""",
            unsafe_allow_html=True,
        )

        diferenca = (
            safe_float(
                best.get("taxa_aprovacao")
            )
            -
            safe_float(
                worst.get("taxa_aprovacao")
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
Distância entre melhor e pior ECV
</div>

</div>
""",
            unsafe_allow_html=True,
        )


# ============================================================
# VISTORIAS
# ============================================================

elif st.session_state.page == "Vistorias":

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

    if df.empty:

        st.info(
            "Nenhuma vistoria disponível."
        )

    else:

        if "data_dt" not in df.columns:

            df["data_dt"] = pd.to_datetime(
                df.get("data_vistoria"),
                errors="coerce",
            )

        valid_dates = (
            df["data_dt"].dropna()
        )

        if not valid_dates.empty:

            mn = valid_dates.min().date()
            mx = valid_dates.max().date()

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
                f = f[f.ecv == ef]

            if (
                cf != "Todas"
                and "cidade" in f.columns
            ):
                f = f[f.cidade == cf]

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

                q = busca.lower().strip()

                mask = pd.Series(
                    False,
                    index=f.index,
                )

                if "placa" in f.columns:

                    mask |= (
                        f["placa"]
                        .astype(str)
                        .str.lower()
                        .str.contains(
                            q,
                            na=False,
                        )
                    )

                if "id" in f.columns:

                    mask |= (
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

                ap = int(
                    (
                        f["resultado"]
                        .astype(str)
                        .str.lower()
                        == "aprovado"
                    ).sum()
                )

                rp = int(
                    (
                        f["resultado"]
                        .astype(str)
                        .str.lower()
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

elif st.session_state.page == "Qualidade":

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

    quality_data = (
        quality_response.get("data")
        or {}
    )

    if isinstance(
        quality_data,
        dict,
    ):

        total = quality_data.get(
            "total",
            quality_data.get(
                "registros",
                len(df),
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
Índice calculado a partir das
inconsistências identificadas.
</div>

</div>
""",
            unsafe_allow_html=True,
        )

        mensagens = quality_data.get(
            "mensagens",
            [],
        )

        for msg in mensagens:
            st.write(msg)

    else:

        st.info(
            "A API não retornou dados de qualidade."
        )


# ============================================================
# IA & INSIGHTS
# ============================================================

elif st.session_state.page == "IA & Insights":

    st.markdown(
        """
<div class="hero">

<h1>IA & Insights</h1>

<p>
Inteligência artificial aplicada à análise operacional das ECVs.
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
Utilize a IA para interpretar indicadores,
identificar oportunidades e apoiar decisões.
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
        placeholder="Qual ECV teve melhor desempenho?",
    )

    st.caption(
        "Exemplos: "
        "Qual ECV teve melhor desempenho? • "
        "Qual teve pior desempenho? • "
        "Quantas vistorias existem?"
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
                    "Não foi possível executar "
                    "o Copilot neste momento."
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
    str(best.get("ecv", "N/D"))
)}
</h3>

<div class="small">
Maior aprovação:
{safe_float(
    best.get("taxa_aprovacao")
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
    str(worst.get("ecv", "N/D"))
)}
</h3>

<div class="small">
Menor aprovação:
{safe_float(
    worst.get("taxa_aprovacao")
):.1f}%
</div>

</div>
""",
            unsafe_allow_html=True,
        )


# ============================================================
# ECVs
# ============================================================

elif st.session_state.page == "ECVs":

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

                performance_join = perf[
                    [
                        "ecv",
                        "taxa_aprovacao",
                    ]
                ].copy()

                display_df = display_df.merge(
                    performance_join,
                    left_on=join_column,
                    right_on="ecv",
                    how="left",
                )

                if join_column != "ecv":

                    display_df = display_df.drop(
                        columns=["ecv"],
                        errors="ignore",
                    )

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# AUTOMAÇÕES
# ============================================================

elif st.session_state.page == "Automações":

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
        sucesso / total * 100
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
        "Operacional",
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
Leitura → Validação → Duplicidades →
Campos críticos → Indicadores → Log
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
            "Nenhuma execução registrada pela API."
        )


# ============================================================
# API
# ============================================================

elif st.session_state.page == "API":

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
        "API",
        "Online",
    )

    c2.metric(
        "Versão",
        "3.0.0",
    )

    c3.metric(
        "Endpoints",
        "15+",
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

    cols = st.columns(2)

    for index, endpoint in enumerate(
        endpoints
    ):

        cols[index % 2].code(
            endpoint
        )

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


# ============================================================
# POWER BI
# ============================================================

elif st.session_state.page == "Power BI":

    st.markdown(
        """
<div class="hero">

<h1>Power BI</h1>

<p>
Camada de integração analítica para consumo dos dados
da plataforma ECV Intelligence.
</p>

</div>
""",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Vistorias",
        "Dataset",
    )

    c2.metric(
        "ECVs",
        "Dataset",
    )

    c3.metric(
        "Indicadores",
        "Dataset",
    )

    st.markdown(
        '<div class="section-title">'
        'Fontes disponíveis'
        '</div>',
        unsafe_allow_html=True,
    )

    a, b, c = st.columns(3)

    with a:

        st.markdown(
            """
<div class="integration-card">

<h3>🚗 Vistorias</h3>

<p>
Dados operacionais das vistorias
para análise no Power BI.
</p>

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
<div class="integration-card">

<h3>🏢 ECVs</h3>

<p>
Dados consolidados das empresas
credenciadas.
</p>

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
<div class="integration-card">

<h3>📊 Indicadores</h3>

<p>
KPIs e indicadores preparados
para camada analítica.
</p>

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
        '<div class="section-title">'
        'Arquitetura de integração'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
<div class="card">

<span class="badge">
BI PIPELINE
</span>

<h3>
ECV Intelligence → API → Power BI
</h3>

<div class="small">

Dados operacionais<br>
↓<br>
FastAPI<br>
↓<br>
Endpoints Power BI<br>
↓<br>
Power BI Dataset<br>
↓<br>
Dashboards executivos

</div>

</div>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# MEU PERFIL
# ============================================================

elif st.session_state.page == "Meu Perfil":

    st.markdown(
        """
<div class="hero">

<h1>Meu Perfil</h1>

<p>
Informações e preferências do usuário da plataforma.
</p>

</div>
""",
        unsafe_allow_html=True,
    )

    a, b = st.columns(2)

    with a:

        st.markdown(
            """
<div class="card">

<span class="badge">
USUÁRIO
</span>

<h3>
Administrador
</h3>

<div class="small">
Perfil com acesso ao ambiente analítico.
</div>

</div>
""",
            unsafe_allow_html=True,
        )

    with b:

        st.markdown(
            """
<div class="card">

<span class="badge">
ACESSO
</span>

<h3>
Analytics + IA
</h3>

<div class="small">
Permissões para análise operacional,
indicadores e inteligência.
</div>

</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="section-title">'
        'Preferências'
        '</div>',
        unsafe_allow_html=True,
    )

    st.checkbox(
        "Receber alertas de desempenho",
        value=True,
    )

    st.checkbox(
        "Exibir indicadores avançados",
        value=True,
    )


# ============================================================
# CONFIGURAÇÕES
# ============================================================

elif st.session_state.page == "Configurações":

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
        """
<div class="card">

<span class="badge">
PLATAFORMA
</span>

<h3>
Preferências gerais
</h3>

<div class="small">
Configure a experiência de utilização do
dashboard.
</div>

</div>
""",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:

        st.checkbox(
            "Atualização automática",
            value=True,
        )

        st.checkbox(
            "Mostrar gráficos avançados",
            value=True,
        )

    with col2:

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
    "ECV Intelligence • Plataforma de "
    "Analytics, IA e Automação"
)


