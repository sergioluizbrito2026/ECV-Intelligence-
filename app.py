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
    background-color: #0f172a;
    color: #f8fafc;
}

/* Sidebar Fixa e Expandida */
[data-testid="stSidebar"] {
    background-color: #0b1120;
    border-right: 1px solid rgba(255,255,255,0.08);
    min-width: 260px !important;
}
[data-testid="stSidebar"] * {
    color: #f8fafc !important;
}
[data-testid="stSidebar"] .stSuccess {
    background-color: rgba(34, 197, 94, 0.15) !important;
    border: 1px solid #22c55e !important;
}
[data-testid="collapsedControl"] {
    display: none;
}

/* Ocultar elementos padrão */
#MainMenu, footer {visibility: hidden;}
header[data-testid="stHeader"] {background: transparent;}

/* Ocupar 100% da largura da tela de forma fluida */
.block-container {
    padding-top: 1.5rem; 
    padding-bottom: 2.5rem; 
    padding-left: 2rem;
    padding-right: 2rem;
    max-width: 100% !important;
}

/* Hero Section */
.hero {
    padding: 1.5rem 1.8rem;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    background: #1e293b;
    margin-bottom: 1.2rem;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
}
.hero h1 {margin:0; font-size:2rem; letter-spacing:-.04em; color: #f8fafc;}
.hero p {margin:.45rem 0 0; color:#94a3b8;}

.section-title {font-size:1.1rem; font-weight:700; margin:1.2rem 0 .8rem; color: #f8fafc;}

/* Métricas e Cards */
[data-testid="stMetric"] {
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 14px 16px;
    background: #1e293b;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
}
[data-testid="stMetric"] label {
    color: #94a3b8 !important;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #f8fafc !important;
}

.card {
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 1.2rem 1.3rem;
    background: #1e293b;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    color: #f8fafc;
}
.card h3 {
    color: #f8fafc !important;
}
.badge {
    display: inline-block; padding:.22rem .55rem; border-radius:999px;
    font-size:.72rem; font-weight:700; background:#334155; color:#f8fafc;
}
.small {font-size:.82rem; color:#94a3b8;}
.trend-up {font-size: 0.8rem; color: #4ade80; font-weight: 600; margin-top: 0.3rem;}
.trend-down {font-size: 0.8rem; color: #f87171; font-weight: 600; margin-top: 0.3rem;}
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

st.sidebar.markdown('<div class="brand" style="font-size:1.1rem; font-weight:bold;">🚗 ECV Intelligence</div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="brand-sub" style="font-size:0.85rem; color:#94a3b8;">Automation • BI • AI</div>', unsafe_allow_html=True)

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

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Vistorias", f"{kpi['total']:,}".replace(",", "."))
    c2.metric("Aprovação", f"{kpi['taxa_aprovacao']:.1f}%")
    c3.metric("Reprovação", f"{kpi['taxa_reprovacao']:.1f}%")
    c4.metric("Tempo médio", f"{kpi['tempo_medio']:.1f} min")
    c5.metric("Faturamento", f"R$ {kpi['faturamento']:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."))

    st.markdown('<div class="section-title">Performance operacional</div>', unsafe_allow_html=True)
    left, right = st.columns(2)

    df_diario = get_daily_series(df)
    df_diario['data'] = pd.to_datetime(df_diario['data'])
    df_diario = df_diario.sort_values('data')

    df_diario['data_fmt'] = df_diario['data'].dt.strftime('%d %b')
    traducao_meses = {
        'Jan': 'jan', 'Feb': 'fev', 'Mar': 'mar', 'Apr': 'abr',
        'May': 'mai', 'Jun': 'jun', 'Jul': 'jul', 'Aug': 'ago',
        'Sep': 'set', 'Oct': 'out', 'Nov': 'nov', 'Dec': 'dez'
    }
    for eng, pt in traducao_meses.items():
        df_diario['data_fmt'] = df_diario['data_fmt'].str.replace(eng, pt, regex=False)

    fig1 = px.line(
        df_diario, 
        x="data_fmt", 
        y="vistorias", 
        markers=True,
        title="Volume de vistorias diárias"
    )
    
    fig1.update_traces(
        fill='tozeroy',
        fillcolor='rgba(56, 189, 248, 0.08)',
        line=dict(color="#38bdf8", width=3),
        marker=dict(size=5, color="#38bdf8", line=dict(width=1, color="#0f172a"))
    )
    
    fig1.update_layout(
        title_font=dict(size=15, color="#f8fafc", family="sans-serif"),
        margin=dict(l=20, r=20, t=50, b=30),
        plot_bgcolor="#1e293b",
        paper_bgcolor="#1e293b",
        font=dict(color="#94a3b8"),
        xaxis=dict(showgrid=False, title_font=dict(color="#94a3b8"), tickfont=dict(color="#94a3b8"), title="data", nticks=12),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", title_font=dict(color="#94a3b8"), tickfont=dict(color="#94a3b8"), title="vistorias")
    )
    left.plotly_chart(fig1, use_container_width=True)

    perf = get_ecv_performance(df)
    fig2 = px.bar(
        perf, 
        x="ecv", 
        y="taxa_aprovacao", 
        color="ecv", 
        text_auto=".1f", 
        title="Taxa de aprovação por ECV (%)"
    )
    fig2.update_traces(marker_line_width=0, opacity=0.9)
    fig2.update_layout(
        title_font=dict(size=15, color="#f8fafc", family="sans-serif"),
        margin=dict(l=20, r=20, t=50, b=20), 
        plot_bgcolor="#1e293b", 
        paper_bgcolor="#1e293b",
        font=dict(color="#94a3b8"),
        xaxis=dict(showgrid=False, title_font=dict(color="#94a3b8"), tickfont=dict(color="#94a3b8")),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", title_font=dict(color="#94a3b8"), tickfont=dict(color="#94a3b8"), title="Aprovação (%)"),
        showlegend=False
    )
    right.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-title">Resumo inteligente</div>', unsafe_allow_html=True)
    best = perf.sort_values("taxa_aprovacao", ascending=False).iloc[0]
    worst = perf.sort_values("taxa_aprovacao").iloc[0]
    
    a, b, c = st.columns(3)
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
    st.markdown("""
    <div class="hero">
      <h1>Vistorias</h1>
      <p>Explore, filtre e exporte os registros operacionais.</p>
    </div>
    """, unsafe_allow_html=True)

    df['data_dt'] = pd.to_datetime(df['data_vistoria'])
    min_date = df['data_dt'].min().date()
    max_date = df['data_dt'].max().date()

    col1, col2, col3 = st.columns(3)
    with col1:
        periodo = st.date_input("Período", [min_date, max_date], min_value=min_date, max_value=max_date)
    with col2:
        ecv_opcoes = ["Todas"] + sorted(df.ecv.unique().tolist())
        ecv_filtro = st.selectbox("ECV", ecv_opcoes)
    with col3:
        cidade_opcoes = ["Todas"] + sorted(df.cidade.unique().tolist())
        cidade_filtro = st.selectbox("Cidade", cidade_opcoes)

    col4, col5, col6 = st.columns(3)
    with col4:
        tipo_opcoes = sorted(df.tipo_vistoria.unique().tolist())
        tipo_filtro = st.multiselect("Tipo de vistoria", tipo_opcoes, default=tipo_opcoes)
    with col5:
        res_opcoes = sorted(df.resultado.unique().tolist())
        res_filtro = st.multiselect("Resultado", res_opcoes, default=res_opcoes)
    with col6:
        busca_filtro = st.text_input("Buscar", placeholder="Placa ou ID")

    if st.button("🔄 Limpar filtros"):
        st.rerun()

    f = df.copy()
    if isinstance(periodo, list) and len(periodo) == 2:
        start_d, end_d = periodo
        f = f[(f['data_dt'].dt.date >= start_d) & (f['data_dt'].dt.date <= end_d)]
    elif isinstance(periodo, tuple) and len(periodo) == 2:
        start_d, end_d = periodo
        f = f[(f['data_dt'].dt.date >= start_d) & (f['data_dt'].dt.date <= end_d)]

    if ecv_filtro != "Todas": f = f[f.ecv == ecv_filtro]
    if cidade_filtro != "Todas": f = f[f.cidade == cidade_filtro]
    if tipo_filtro: f = f[f.tipo_vistoria.isin(tipo_filtro)]
    if res_filtro: f = f[f.resultado.isin(res_filtro)]
    if busca_filtro:
        termo = busca_filtro.strip().lower()
        f = f[f['placa'].str.lower().str.contains(termo, na=False) | f['id'].astype(str).str.contains(termo, na=False)]

    st.divider()

    total_f = len(f)
    if total_f > 0:
        aprovadas_f = len(f[f['resultado'] == 'Aprovado'])
        reprovadas_f = len(f[f['resultado'] == 'Reprovado'])
        taxa_aprov_f = (aprovadas_f / total_f) * 100
        taxa_reprov_f = (reprovadas_f / total_f) * 100
        tempo_medio_f = f['tempo_minutos'].mean()
        faturamento_f = f['valor'].sum() if 'valor' in f.columns else 0
    else:
        taxa_aprov_f, taxa_reprov_f, tempo_medio_f, faturamento_f = 0, 0, 0, 0

    ic1, ic2, ic3, ic4 = st.columns(4)
    ic1.metric("Vistorias", f"{total_f:,}".replace(",", "."))
    ic2.metric("Aprovação", f"{taxa_aprov_f:.1f}%")
    ic3.metric("Reprovação", f"{taxa_reprov_f:.1f}%")
    ic4.metric("Tempo médio", f"{tempo_medio_f:.1f} min")

    st.markdown(f'<div class="section-title">Registros encontrados: {total_f:,}</div>'.replace(",", "."), unsafe_allow_html=True)

    st.dataframe(
        f[["id", "data_vistoria", "ecv", "cidade", "placa", "tipo_vistoria", "resultado", "tempo_minutos", "valor"]],
        use_container_width=True,
        hide_index=True
    )
    st.download_button("📥 Exportar CSV", f.to_csv(index=False).encode("utf-8"), "vistorias_filtradas.csv", "text/csv")

elif page == "Qualidade":
    st.markdown("""
    <div class="hero">
      <h1>Qualidade dos Dados</h1>
      <p>Diagnóstico e monitoramento da confiabilidade da base e conformidade estrutural.</p>
    </div>
    """, unsafe_allow_html=True)

    report = get_quality_report(df)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registros", report["total"])
    c2.metric("Duplicados", report["duplicados"])
    c3.metric("Campos vazios", report["nulos"])
    c4.metric("Placas inválidas", report["placas_invalidas"])

    st.markdown("<br>", unsafe_allow_html=True)
    col_score, col_dist = st.columns([1, 1])

    with col_score:
        st.markdown('''
        <div class="card" style="height: 100%;">
            <span class="badge">SCORE DE QUALIDADE</span>
            <div style="text-align: center; margin: 1.2rem 0;">
                <span style="font-size: 3rem; font-weight: 800; color: #4ade80;">100%</span>
                <div style="font-size: 1.1rem; font-weight: 600; color: #f8fafc; margin-top: 0.2rem;">Excelente</div>
            </div>
            <div style="font-size: 0.9rem; color: #94a3b8; line-height: 1.6;">
                ✓ Base consistente<br>
                ✓ Integridade referencial válida<br>
                ✓ Ausência de anomalias estruturais
            </div>
        </div>
        ''', unsafe_allow_html=True)

    with col_dist:
        st.markdown('''
        <div class="card" style="height: 100%;">
            <span class="badge">DISTRIBUIÇÃO DA QUALIDADE</span>
            <div style="margin-top: 1rem; font-size: 0.9rem;">
                <div style="margin-bottom: 0.8rem;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:0.2rem;">
                        <span>Completude</span><span>100%</span>
                    </div>
                    <div style="background:#334155; border-radius:999px; height:8px;"><div style="background:#38bdf8; width:100%; height:8px; border-radius:999px;"></div></div>
                </div>
                <div style="margin-bottom: 0.8rem;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:0.2rem;">
                        <span>Unicidade</span><span>100%</span>
                    </div>
                    <div style="background:#334155; border-radius:999px; height:8px;"><div style="background:#38bdf8; width:100%; height:8px; border-radius:999px;"></div></div>
                </div>
                <div style="margin-bottom: 0.8rem;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:0.2rem;">
                        <span>Formato</span><span>100%</span>
                    </div>
                    <div style="background:#334155; border-radius:999px; height:8px;"><div style="background:#38bdf8; width:100%; height:8px; border-radius:999px;"></div></div>
                </div>
                <div>
                    <div style="display:flex; justify-content:space-between; margin-bottom:0.2rem;">
                        <span>Consistência</span><span>100%</span>
                    </div>
                    <div style="background:#334155; border-radius:999px; height:8px;"><div style="background:#38bdf8; width:100%; height:8px; border-radius:999px;"></div></div>
                </div>
            </div>
        </div>
        ''', unsafe_allow_html=True)

elif page == "Automações":
    st.markdown("""
    <div class="hero">
      <h1>Central de Automações & IA</h1>
      <p>Automatize processos, analise dados com inteligência artificial e acompanhe resultados de ponta a ponta.</p>
    </div>
    """, unsafe_allow_html=True)

    k1, k2, k3, k4, k5 = st.columns(5)
    st.markdown("""
    <div class="hero">
      <h1>Central de Automações & IA</h1>
      <p>Automatize processos, analise dados com inteligência artificial e acompanhe resultados de ponta a ponta.</p>
    </div>
    """, unsafe_allow_html=True)

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Automações", "12")
    k2.metric("Execuções", "1.248")
    k3.metric("Sucesso", "98,4%")
    k4.metric("Tempo poupado", "42h/mês")
    k5.metric("Insights IA", "18 geradas")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">Pipeline de Dados em Tempo Real</div>', unsafe_allow_html=True)
    st.markdown("""
                
                             
        
    </div>
    """, unsafe_allow_html=True)

    # Botão de execução do pipeline
    if st.button("🚀 Executar pipeline completo", type="primary", use_container_width=True):
        with st.spinner("Executando pipeline de ponta a ponta..."):
            run_pipeline()
        st.success("Pipeline executado com sucesso e logs gravados no SQLite.")

    # --- ADIÇÃO DA TABELA DE LOGS PROFISSIONAL ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">📋 Histórico de Execuções (Logs)</div>', unsafe_allow_html=True)

    def load_logs():
        conn = get_connection()
        logs_df = pd.read_sql_query("SELECT * FROM logs_automacao ORDER BY id DESC LIMIT 10", conn)
        conn.close()
        return logs_df

    df_logs = load_logs()
    
    if not df_logs.empty:
        st.dataframe(df_logs, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum log registrado até o momento. Execute o pipeline acima.")

elif page == "IA & Insights":
    st.markdown("""
    <div class="hero">
      <h1>IA & Insights</h1>
      <p>Inteligência artificial aplicada à análise operacional dos ECVs.</p>
    </div>
    """, unsafe_allow_html=True)

    # 1. Topo: KPIs de IA
    i1, i2, i3, i4 = st.columns(4)
    i1.metric("Insights IA", "18")
    i2.metric("Anomalias", "3")
    i3.metric("Perguntas", "42")
    i4.metric("Recomendações", "7")

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Análise Executiva com IA
    st.markdown('<div class="section-title">🤖 Análise Executiva com IA</div>', unsafe_allow_html=True)
    if st.button("✨ Gerar análise executiva", type="primary", use_container_width=True):
        perf_data = get_ecv_performance(df)
        with st.spinner("Analisando 5.000 registros e calculando indicadores..."):
            analise_gerada = analyze_data(kpi, perf_data)
        st.markdown(f'<div class="card" style="margin-top: 1rem;"><b style="color: #38bdf8;">Resumo Executivo (Baseado em SQLite):</b><br><br>{analise_gerada}</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="small" style="margin-top: 0.5rem; color: #94a3b8;">
        
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Insights Identificados & 4. Detecção de Anomalias
    col_ins_left, col_ins_right = st.columns(2)

    with col_ins_left:
        st.markdown('''
        <div class="card" style="height: 100%;">
            <span class="badge">🧠 INSIGHTS IDENTIFICADOS</span>
            <div style="display: grid; grid-template-columns: 1fr; gap: 1rem; margin-top: 1rem;">
                <div style="background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.2); padding: 1rem; border-radius: 10px;">
                    <span style="color: #f59e0b; font-size: 0.75rem; font-weight: 700;">⚠️ PONTO DE ATENÇÃO</span>
                    <div style="font-size: 0.9rem; margin: 0.3rem 0;">ECV Oeste apresenta reprovação acima da média geral.</div>
                    <div style="font-size: 0.8rem; color: #94a3b8;">Prioridade: <b>ALTA</b></div>
                </div>
                <div style="background: rgba(34, 197, 94, 0.08); border: 1px solid rgba(34, 197, 94, 0.2); padding: 1rem; border-radius: 10px;">
                    <span style="color: #4ade80; font-size: 0.75rem; font-weight: 700;">📈 OPORTUNIDADE</span>
                    <div style="font-size: 0.9rem; margin: 0.3rem 0;">ECV Alpha apresenta melhor desempenho operacional.</div>
                    <div style="font-size: 0.8rem; color: #94a3b8;">Impacto: <b>ALTO</b></div>
                </div>
            </div>
        </div>
        ''', unsafe_allow_html=True)

    with col_ins_right:
        st.markdown('''
        <div class="card" style="height: 100%;">
            <span class="badge">🔍 DETECÇÃO DE ANOMALIAS</span>
            <h3 style="margin: 0.6rem 0 0.4rem 0;">🔴 ECV Oeste</h3>
            <div style="font-size: 0.9rem; display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.8rem; background: #0f172a; padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                <div><div style="color: #94a3b8; font-size: 0.75rem;">Reprovação</div><div style="font-weight: 700; color: #f87171; font-size: 1.1rem;">25,6%</div></div>
                <div><div style="color: #94a3b8; font-size: 0.75rem;">Média Geral</div><div style="font-weight: 700; font-size: 1.1rem;">13,7%</div></div>
            </div>
            <div style="font-size: 0.9rem; margin-bottom: 1rem;"><b>Desvio:</b> <span style="color: #f87171; font-weight: 700;">+11,9 p.p.</span></div>
        ''', unsafe_allow_html=True)
        if st.button("Analisar causa", key="btn_anomalia"):
            st.info("Causa sugerida: Concentração de reprovações em vistoria estrutural e de itens de segurança no período noturno.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 5. Pergunte aos dados (Copilot integrado ao SQLite)
    st.markdown('<div class="section-title">💬 Pergunte aos dados (ECV Intelligence Copilot)</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    pergunta_usuario = st.text_input("Ex: Qual ECV possui maior taxa de reprovação?", placeholder="Qual ECV precisa de mais atenção?")
    if st.button("🔎 Consultar", type="primary"):
        if pergunta_usuario:
            with st.spinner("Consultando SQLite e interpretando com LLM..."):
                resposta_copilot = ask_data(pergunta_usuario, df)
            st.markdown(f'<div style="background: #0f172a; padding: 1rem; border-radius: 8px; margin-top: 1rem; border: 1px solid rgba(56,189,248,0.2);"><b style="color: #38bdf8;">Resposta do Copilot:</b><br>{resposta_copilot}</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="small" style="margin-top: 1rem; color: #94a3b8;">
        
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif page == "API":
    st.markdown('<div class="hero"><h1>API & Integrações</h1><p>Camada REST demonstrativa para integração com sistemas internos e BI.</p></div>', unsafe_allow_html=True)
    st.subheader("Endpoints")
    for ep in ["GET /health", "GET /ecvs", "GET /vistorias", "GET /indicadores"]:
        st.code(ep)
    st.markdown("Execute a API em um terminal:")
    st.code("uvicorn services.api_service:app --reload --port 8000", language="bash")
    st.info("A aplicação principal funciona sem iniciar a API. Ela está incluída para demonstrar integração entre sistemas.")
