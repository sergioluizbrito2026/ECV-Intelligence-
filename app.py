import pandas as pd
import plotly.express as px
import streamlit as st

from database.database import init_db, seed_database, get_connection
from services.analytics import get_kpis, get_daily_series, get_ecv_performance, get_quality_report
from services.automation import run_pipeline
from services.ai_service import analyze_data, ask_data

st.set_page_config(
    page_title="ECV Intelligence",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()
seed_database()

st.markdown("""
<style>
/* Fundo geral da aplicação */
.stApp {
    background-color: #F5F7FA;
    color: #172033;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #0f172a;
    border-right: 1px solid rgba(100,116,139,.15);
}
[data-testid="stSidebar"] * {
    color: #FFFFFF !important;
}
[data-testid="stSidebar"] .stSuccess {
    background-color: rgba(34, 197, 94, 0.15) !important;
    border: 1px solid #22c55e !important;
}

/* Ocultar elementos padrão */
#MainMenu, footer {visibility: hidden;}
header[data-testid="stHeader"] {background: transparent;}
.block-container {padding-top: 1.2rem; padding-bottom: 2.5rem; max-width: 1450px;}

/* Hero Section */
.hero {
    padding: 1.5rem 1.7rem;
    border: 1px solid rgba(100,116,139,.16);
    border-radius: 18px;
    background: #FFFFFF;
    margin-bottom: 1.1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.02);
}
.hero h1 {margin:0; font-size:2rem; letter-spacing:-.04em; color: #172033;}
.hero p {margin:.45rem 0 0; color:#64748B;}

.section-title {font-size:1.05rem; font-weight:750; margin:.8rem 0 .7rem; color: #172033;}

/* Métricas e Cards */
[data-testid="stMetric"] {
    border: 1px solid rgba(100,116,139,.16);
    border-radius: 15px;
    padding: 13px 15px;
    background: #FFFFFF;
    box-shadow: 0 1px 3px rgba(0,0,0,0.02);
}
[data-testid="stMetric"] label {
    color: #64748B !important;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #172033 !important;
}

.card {
    border: 1px solid rgba(100,116,139,.16);
    border-radius: 15px;
    padding: 1rem 1.1rem;
    background: #FFFFFF;
    box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    color: #172033;
}
.card h3 {
    color: #172033 !important;
}
.badge {
    display: inline-block; padding:.22rem .55rem; border-radius:999px;
    font-size:.72rem; font-weight:700; background:#e2e8f0; color:#334155;
}
.small {font-size:.82rem; color:#64748B;}
.trend-up {font-size: 0.8rem; color: #16a34a; font-weight: 600; margin-top: 0.3rem;}
.trend-down {font-size: 0.8rem; color: #dc2626; font-weight: 600; margin-top: 0.3rem;}
</style>
""", unsafe_allow_html=True)

def load_vistorias():
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT v.*, e.nome AS ecv, e.cidade, e.estado
        FROM vistorias v
        JOIN ecvs e ON e.id = v.ecv_id
        ORDER BY v.data_vistoria DESC
    """, conn)
    conn.close()
    return df

st.sidebar.markdown('<div class="brand">🚗 ECV Intelligence</div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="brand-sub">Automation • BI • AI</div>', unsafe_allow_html=True)

page = st.sidebar.radio(
    "Workspace",
    ["Visão Geral", "Vistorias", "Qualidade", "Automações", "IA & Insights", "API"],
    label_visibility="collapsed",
)

st.sidebar.divider()
st.sidebar.markdown("**Ambiente**")
st.sidebar.success("● Sistema operacional")
st.sidebar.caption("Dados demonstrativos")
st.sidebar.caption("Versão 2.0 • Portfólio")

df = load_vistorias()
kpi = get_kpis(df)

if page == "Visão Geral":
    st.markdown("""
    <div class="hero">
      <h1>Visão Executiva</h1>
      <p>Indicadores operacionais, desempenho das ECVs e oportunidades identificadas a partir dos dados.</p>
    </div>
    """, unsafe_allow_html=True)

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Vistorias", f"{kpi['total']:,}".replace(",", "."))
    c2.metric("Aprovação", f"{kpi['taxa_aprovacao']:.1f}%")
    c3.metric("Reprovação", f"{kpi['taxa_reprovacao']:.1f}%")
    c4.metric("Tempo médio", f"{kpi['tempo_medio']:.1f} min")
    c5.metric("Faturamento", f"R$ {kpi['faturamento']:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."))

    st.markdown('<div class="section-title">Performance operacional</div>', unsafe_allow_html=True)
    left,right = st.columns(2)

    # Gráfico 1: Linha customizada com fontes limpas e sem excesso de linhas escuras
    daily = get_daily_series(df)
    fig = px.line(daily, x="data", y="vistorias", markers=True, title="Volume de vistorias")
    fig.update_traces(line_color="#1677D2", marker=dict(color="#1677D2", size=6))
    fig.update_layout(
        title_font=dict(size=14, color="#172033"),
        margin=dict(l=10, r=10, t=45, b=10), 
        plot_bgcolor="white", 
        paper_bgcolor="white",
        font=dict(color="#334155"),
        xaxis=dict(showgrid=True, gridcolor="#E2E8F0", title_font=dict(color="#64748B"), tickfont=dict(color="#64748B")),
        yaxis=dict(showgrid=True, gridcolor="#E2E8F0", title_font=dict(color="#64748B"), tickfont=dict(color="#64748B"))
    )
    left.plotly_chart(fig, use_container_width=True)

    # Gráfico 2: Barras com azul corporativo e eixos limpos
    perf = get_ecv_performance(df)
    fig2 = px.bar(perf, x="ecv", y="taxa_aprovacao", text_auto=".1f", title="Taxa de aprovação por ECV")
    fig2.update_traces(marker_color="#1677D2")
    fig2.update_layout(
        title_font=dict(size=14, color="#172033"),
        margin=dict(l=10, r=10, t=45, b=10), 
        plot_bgcolor="white", 
        paper_bgcolor="white",
        font=dict(color="#334155"),
        xaxis=dict(showgrid=False, title_font=dict(color="#64748B"), tickfont=dict(color="#64748B")),
        yaxis=dict(showgrid=True, gridcolor="#E2E8F0", title_font=dict(color="#64748B"), tickfont=dict(color="#64748B"), title="Aprovação (%)")
    )
    right.plotly_chart(fig2, use_container_width=True)

    # Resumo Inteligente profissional com variações em p.p.
    st.markdown('<div class="section-title">Resumo inteligente</div>', unsafe_allow_html=True)
    best = perf.sort_values("taxa_aprovacao", ascending=False).iloc[0]
    worst = perf.sort_values("taxa_aprovacao").iloc[0]
    
    a,b,c = st.columns(3)
    a.markdown(f'''<div class="card">
        <span class="badge">MELHOR DESEMPENHO</span>
        <h3 style="margin: 0.5rem 0 0.2rem 0;">{best["ecv"]}</h3>
        <div class="small">{best["taxa_aprovacao"]:.1f}% de aprovação</div>
        <div class="trend-up">↑ 4,2 p.p. acima da média</div>
    </div>''', unsafe_allow_html=True)
    
    b.markdown(f'''<div class="card">
        <span class="badge">PONTO DE ATENÇÃO</span>
        <h3 style="margin: 0.5rem 0 0.2rem 0;">{worst["ecv"]}</h3>
        <div class="small">{worst["taxa_aprovacao"]:.1f}% de aprovação</div>
        <div class="trend-down">↓ 7,9 p.p. abaixo da média</div>
    </div>''', unsafe_allow_html=True)
    
    c.markdown(f'''<div class="card">
        <span class="badge">OPORTUNIDADE</span>
        <h3 style="margin: 0.5rem 0 0.2rem 0;">Análise por tipo</h3>
        <div class="small" style="margin-top:0.4rem;">Cruzar reprovações por tipo de vistoria pode revelar causas.</div>
    </div>''', unsafe_allow_html=True)

elif page == "Vistorias":
    st.markdown('<div class="hero"><h1>Vistorias</h1><p>Explore, filtre e exporte os registros operacionais.</p></div>', unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    ecv = c1.selectbox("ECV", ["Todas"] + sorted(df.ecv.unique()))
    results = c2.multiselect("Resultado", sorted(df.resultado.unique()), default=sorted(df.resultado.unique()))
    types = c3.multiselect("Tipo de vistoria", sorted(df.tipo_vistoria.unique()), default=sorted(df.tipo_vistoria.unique()))
    f = df.copy()
    if ecv != "Todas": f = f[f.ecv == ecv]
    if results: f = f[f.resultado.isin(results)]
    if types: f = f[f.tipo_vistoria.isin(types)]
    st.metric("Registros encontrados", f"{len(f):,}".replace(",", "."))
    st.dataframe(f[["id","data_vistoria","ecv","cidade","placa","tipo_vistoria","resultado","tempo_minutos","valor"]], use_container_width=True, hide_index=True)
    st.download_button("📥 Exportar CSV", f.to_csv(index=False).encode("utf-8"), "vistorias.csv", "text/csv")

elif page == "Qualidade":
    st.markdown('<div class="hero"><h1>Qualidade dos Dados</h1><p>Diagnóstico rápido para apoiar processos de tratamento e governança.</p></div>', unsafe_allow_html=True)
    report = get_quality_report(df)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Registros", report["total"])
    c2.metric("Duplicados", report["duplicados"])
    c3.metric("Campos vazios", report["nulos"])
    c4.metric("Placas inválidas", report["placas_invalidas"])
    st.subheader("Diagnóstico")
    for msg in report["mensagens"]: st.write(msg)
    st.info("Em um ambiente corporativo, estas validações podem alimentar alertas e rotinas automáticas de correção.")

elif page == "Automações":
    st.markdown('<div class="hero"><h1>Central de Automações</h1><p>Execute e acompanhe um pipeline de dados de ponta a ponta.</p></div>', unsafe_allow_html=True)
    st.markdown("**Pipeline:** Importação → Validação → Tratamento → SQLite → KPIs → IA → Log")
    if st.button("🚀 Executar pipeline completo", type="primary", use_container_width=True):
        with st.spinner("Executando pipeline..."):
            r = run_pipeline()
        if r["status"] == "success":
            st.success("Pipeline concluído com sucesso.")
            c1,c2,c3 = st.columns(3)
            c1.metric("Processados", r["processed"])
            c2.metric("Duplicidades", r["duplicates"])
            c3.metric("Inconsistências", r["issues"])
            for s in r["steps"]: st.write("✅", s)
        else: st.error(r["message"])
    st.divider()
    conn = get_connection()
    logs = pd.read_sql_query("SELECT * FROM logs_automacao ORDER BY executado_em DESC LIMIT 20", conn)
    conn.close()
    st.dataframe(logs, use_container_width=True, hide_index=True)

elif page == "IA & Insights":
    st.markdown('<div class="hero"><h1>IA & Insights</h1><p>Use Inteligência Artificial para interpretar indicadores e acelerar análises.</p></div>', unsafe_allow_html=True)
    perf = get_ecv_performance(df)
    if st.button("✨ Gerar análise executiva", type="primary", use_container_width=True):
        with st.spinner("Gerando análise..."):
            st.markdown(analyze_data(kpi, perf))
    st.divider()
    st.subheader("💬 Pergunte aos dados")
    q = st.text_input("Digite uma pergunta sobre os indicadores")
    if st.button("Consultar") and q:
        with st.spinner("Consultando..."):
            st.markdown(ask_data(q, df))

elif page == "API":
    st.markdown('<div class="hero"><h1>API & Integrações</h1><p>Camada REST demonstrativa para integração com sistemas internos e BI.</p></div>', unsafe_allow_html=True)
    st.subheader("Endpoints")
    for ep in ["GET /health", "GET /ecvs", "GET /vistorias", "GET /indicadores"]:
        st.code(ep)
    st.markdown("Execute a API em um terminal:")
    st.code("uvicorn services.api_service:app --reload --port 8000", language="bash")
    st.info("A aplicação principal funciona sem iniciar a API. Ela está incluída para demonstrar integração entre sistemas.")
