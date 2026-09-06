import html
import pandas as pd
import plotly.express as px
import streamlit as st

from database.database import init_db, seed_database, get_connection
from services.analytics import get_kpis, get_daily_series, get_ecv_performance, get_quality_report
from services.automation import run_pipeline
from services.ai_service import analyze_data, ask_data

st.set_page_config(page_title="ECV Intelligence", page_icon="🚗", layout="wide")

@st.cache_resource
def bootstrap():
    init_db()
    seed_database()
    return True

bootstrap()

st.markdown("""
<style>
.stApp{background:#0f172a;color:#f8fafc}
[data-testid="stSidebar"]{background:#0b1120;border-right:1px solid rgba(255,255,255,.08);min-width:260px!important}
[data-testid="stSidebar"] *{color:#f8fafc!important}
#MainMenu,footer{visibility:hidden}
.block-container{padding:1.5rem 2rem 2.5rem;max-width:100%!important}
.hero{padding:1.5rem 1.8rem;border:1px solid rgba(255,255,255,.08);border-radius:16px;background:#1e293b;margin-bottom:1.2rem}
.hero h1{margin:0;font-size:2rem;color:#f8fafc}.hero p{margin:.45rem 0 0;color:#94a3b8}
.section-title{font-size:1.1rem;font-weight:700;margin:1.2rem 0 .8rem}
[data-testid="stMetric"]{border:1px solid rgba(255,255,255,.08);border-radius:14px;padding:14px 16px;background:#1e293b}
[data-testid="stMetric"] label{color:#94a3b8!important}
[data-testid="stMetric"] [data-testid="stMetricValue"]{color:#f8fafc!important}
.card{border:1px solid rgba(255,255,255,.08);border-radius:14px;padding:1.2rem 1.3rem;background:#1e293b;color:#f8fafc}
.badge{display:inline-block;padding:.22rem .55rem;border-radius:999px;font-size:.72rem;font-weight:700;background:#334155}
.small{font-size:.82rem;color:#94a3b8}.success{color:#4ade80}.danger{color:#f87171}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=30)
def load_vistorias():
    conn = get_connection()
    try:
        return pd.read_sql_query("""
            SELECT v.id,v.ecv_id,v.placa,v.tipo_vistoria,v.data_vistoria,
                   v.resultado,v.tempo_minutos,v.valor,
                   e.nome AS ecv,e.cidade,e.estado
            FROM vistorias v
            JOIN ecvs e ON e.id=v.ecv_id
            ORDER BY v.data_vistoria DESC
        """, conn)
    finally:
        conn.close()

@st.cache_data(ttl=15)
def load_logs():
    conn = get_connection()
    try:
        return pd.read_sql_query(
            "SELECT * FROM logs_automacao ORDER BY id DESC LIMIT 20", conn
        )
    finally:
        conn.close()

def number(v):
    return f"{v:,.0f}".replace(",", ".")

def money(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

df = load_vistorias()
if df.empty:
    st.warning("Nenhuma vistoria encontrada.")
    st.stop()

df["data_dt"] = pd.to_datetime(df["data_vistoria"], errors="coerce")
kpi = get_kpis(df)
perf = get_ecv_performance(df)

st.sidebar.markdown("""
<div style="padding:10px 0">
<h3 style="margin:0">📊 ECV Intelligence</h3>
<p style="margin:4px 0;color:#94a3b8;font-size:.8rem">Analytics, IA e automação para ECVs</p>
</div>
""", unsafe_allow_html=True)

page = st.sidebar.radio(
    "Workspace",
    ["Visão Geral","Vistorias","Qualidade","Automações","IA & Insights","ECVs","API"],
    label_visibility="collapsed",
)
st.sidebar.divider()
st.sidebar.markdown("**Ambiente**")
st.sidebar.success("● Sistema operacional")
st.sidebar.caption("Organização: ECV Intelligence Demo")
st.sidebar.caption("Plano: Demo")
st.sidebar.caption("V3 • SaaS-ready")

if page == "Visão Geral":
    st.markdown('<div class="hero"><h1>Visão Executiva</h1><p>Monitoramento operacional, desempenho das ECVs e inteligência para tomada de decisão.</p></div>', unsafe_allow_html=True)
    c1,c2,c3,c4,c5=st.columns(5)
    c1.metric("Vistorias",number(kpi["total"]))
    c2.metric("Aprovação",f'{kpi["taxa_aprovacao"]:.1f}%')
    c3.metric("Reprovação",f'{kpi["taxa_reprovacao"]:.1f}%')
    c4.metric("Tempo médio",f'{kpi["tempo_medio"]:.1f} min')
    c5.metric("Faturamento",money(kpi["faturamento"]))

    st.markdown('<div class="section-title">Performance operacional</div>',unsafe_allow_html=True)
    a,b=st.columns(2)
    daily=get_daily_series(df)
    daily["data"]=pd.to_datetime(daily["data"])
    fig1=px.line(daily,x="data",y="vistorias",markers=True,title="Volume diário de vistorias")
    fig1.update_layout(plot_bgcolor="#1e293b",paper_bgcolor="#1e293b",font=dict(color="#94a3b8"),margin=dict(l=20,r=20,t=50,b=30))
    a.plotly_chart(fig1,use_container_width=True)

    fig2=px.bar(perf,x="ecv",y="taxa_aprovacao",text_auto=".1f",title="Taxa de aprovação por ECV (%)")
    fig2.update_layout(plot_bgcolor="#1e293b",paper_bgcolor="#1e293b",font=dict(color="#94a3b8"),margin=dict(l=20,r=20,t=50,b=30),showlegend=False)
    b.plotly_chart(fig2,use_container_width=True)

    best=perf.iloc[0]; worst=perf.iloc[-1]
    x,y,z=st.columns(3)
    x.markdown(f'<div class="card"><span class="badge">MELHOR DESEMPENHO</span><h3>{html.escape(str(best["ecv"]))}</h3><div class="success">{best["taxa_aprovacao"]:.1f}% de aprovação</div></div>',unsafe_allow_html=True)
    y.markdown(f'<div class="card"><span class="badge">PONTO DE ATENÇÃO</span><h3>{html.escape(str(worst["ecv"]))}</h3><div class="danger">{worst["taxa_aprovacao"]:.1f}% de aprovação</div></div>',unsafe_allow_html=True)
    z.markdown(f'<div class="card"><span class="badge">DIFERENCIAL</span><h3>{best["taxa_aprovacao"]-worst["taxa_aprovacao"]:.1f} p.p.</h3><div class="small">distância entre melhor e pior ECV</div></div>',unsafe_allow_html=True)

elif page == "Vistorias":
    st.markdown('<div class="hero"><h1>Vistorias</h1><p>Pesquisa, filtros e exportação dos registros operacionais.</p></div>',unsafe_allow_html=True)
    mn=df["data_dt"].min().date(); mx=df["data_dt"].max().date()
    c1,c2,c3=st.columns(3)
    with c1: periodo=st.date_input("Período",[mn,mx],min_value=mn,max_value=mx)
    with c2: ef=st.selectbox("ECV",["Todas"]+sorted(df.ecv.dropna().unique().tolist()))
    with c3: cf=st.selectbox("Cidade",["Todas"]+sorted(df.cidade.dropna().unique().tolist()))
    c4,c5,c6=st.columns(3)
    with c4:
        tipos=sorted(df.tipo_vistoria.dropna().unique().tolist()); tf=st.multiselect("Tipo",tipos,default=tipos)
    with c5:
        res=sorted(df.resultado.dropna().unique().tolist()); rf=st.multiselect("Resultado",res,default=res)
    with c6: busca=st.text_input("Buscar","",placeholder="Placa ou ID")
    f=df.copy()
    if isinstance(periodo,(list,tuple)) and len(periodo)==2:
        f=f[(f.data_dt.dt.date>=periodo[0])&(f.data_dt.dt.date<=periodo[1])]
    if ef!="Todas": f=f[f.ecv==ef]
    if cf!="Todas": f=f[f.cidade==cf]
    if tf: f=f[f.tipo_vistoria.isin(tf)]
    if rf: f=f[f.resultado.isin(rf)]
    if busca:
        q=busca.lower().strip()
        f=f[f.placa.astype(str).str.lower().str.contains(q,na=False)|f.id.astype(str).str.contains(q,na=False)]
    a,b,c,d=st.columns(4)
    total=len(f); ap=int((f.resultado=="Aprovado").sum()) if total else 0; rp=int((f.resultado=="Reprovado").sum()) if total else 0
    a.metric("Registros",number(total)); b.metric("Aprovação",f"{ap/total*100:.1f}%" if total else "0,0%"); c.metric("Reprovação",f"{rp/total*100:.1f}%" if total else "0,0%"); d.metric("Faturamento",money(float(f.valor.sum())) if total else "R$ 0,00")
    cols=["id","data_vistoria","ecv","cidade","placa","tipo_vistoria","resultado","tempo_minutos","valor"]
    st.dataframe(f[cols],use_container_width=True,hide_index=True)
    st.download_button("📥 Exportar CSV",f.to_csv(index=False).encode("utf-8"),"vistorias_filtradas.csv","text/csv")

elif page == "Qualidade":
    st.markdown('<div class="hero"><h1>Qualidade dos Dados</h1><p>Diagnóstico da confiabilidade da base operacional.</p></div>',unsafe_allow_html=True)
    r=get_quality_report(df)
    a,b,c,d=st.columns(4)
    a.metric("Registros",number(r["total"])); b.metric("Duplicados",number(r["duplicados"])); c.metric("Campos vazios",number(r["nulos"])); d.metric("Placas inválidas",number(r["placas_invalidas"]))
    score=max(0,100-(r["duplicados"]+r["nulos"]+r["placas_invalidas"])/r["total"]*100) if r["total"] else 0
    st.markdown(f'<div class="card"><span class="badge">SCORE DE QUALIDADE</span><h2>{score:.1f}%</h2><div class="small">Calculado a partir das inconsistências identificadas.</div></div>',unsafe_allow_html=True)
    for msg in r.get("mensagens",[]): st.write(msg)

elif page == "Automações":
    st.markdown('<div class="hero"><h1>Central de Automações</h1><p>Validação, monitoramento e histórico das execuções.</p></div>',unsafe_allow_html=True)
    logs=load_logs()
    total=len(logs)
    sucesso=int(logs.status.astype(str).str.lower().eq("concluído").sum()) if total else 0
    taxa=sucesso/total*100 if total else 0
    processados=int(pd.to_numeric(logs.registros_processados,errors="coerce").fillna(0).sum()) if total else 0
    a,b,c,d=st.columns(4)
    a.metric("Execuções",number(total)); b.metric("Sucesso",f"{taxa:.1f}%"); c.metric("Processados",number(processados)); d.metric("Status","Operacional")
    st.markdown('<div class="card"><span class="badge">PIPELINE</span><h3>Validação operacional</h3><div class="small">Leitura → Validação → Duplicidades → Campos críticos → Indicadores → Log</div></div>',unsafe_allow_html=True)
    if st.button("🚀 Executar pipeline completo",type="primary",use_container_width=True):
        with st.spinner("Executando pipeline..."): result=run_pipeline()
        if result.get("status")=="success":
            st.success(f'Pipeline concluído: {number(result.get("processed",0))} registros processados.')
            st.cache_data.clear(); st.rerun()
        else: st.error(result.get("message","Falha na execução."))
    st.markdown('<div class="section-title">📋 Histórico</div>',unsafe_allow_html=True)
    st.dataframe(logs,use_container_width=True,hide_index=True) if not logs.empty else st.info("Nenhuma execução registrada.")

elif page == "IA & Insights":
    st.markdown('<div class="hero"><h1>IA & Insights</h1><p>Inteligência artificial aplicada à análise operacional das ECVs.</p></div>',unsafe_allow_html=True)
    a,b,c=st.columns(3)
    a.metric("ECVs analisadas",number(perf.ecv.nunique())); b.metric("Vistorias analisadas",number(len(df))); c.metric("Copilot","Ativo")
    if st.button("✨ Gerar análise executiva",type="primary",use_container_width=True):
        with st.spinner("Analisando indicadores..."): answer=analyze_data(kpi,perf)
        st.markdown(f'<div class="card"><span class="badge">ECV INTELLIGENCE AI</span><div style="margin-top:1rem">{answer}</div></div>',unsafe_allow_html=True)
    st.markdown('<div class="section-title">💬 Copilot de Dados</div>',unsafe_allow_html=True)
    question=st.text_input("Pergunta",placeholder="Qual ECV teve melhor desempenho?")
    st.caption("Exemplos: Qual ECV teve melhor desempenho? • Qual teve pior desempenho? • Quantas vistorias existem?")
    if st.button("🔎 Consultar dados",type="primary"):
        if not question.strip(): st.warning("Digite uma pergunta.")
        else:
            with st.spinner("Consultando dados..."): answer=ask_data(question,df)
            st.markdown(f'<div class="card"><span class="badge">COPILOT</span><div style="margin-top:1rem">{answer}</div></div>',unsafe_allow_html=True)
    best=perf.iloc[0]; worst=perf.iloc[-1]
    x,y=st.columns(2)
    x.markdown(f'<div class="card"><span class="badge">OPORTUNIDADE</span><h3>{html.escape(str(best["ecv"]))}</h3><div class="small">Maior aprovação: {best["taxa_aprovacao"]:.1f}%</div></div>',unsafe_allow_html=True)
    y.markdown(f'<div class="card"><span class="badge">ATENÇÃO</span><h3>{html.escape(str(worst["ecv"]))}</h3><div class="small">Menor aprovação: {worst["taxa_aprovacao"]:.1f}%</div></div>',unsafe_allow_html=True)

elif page == "ECVs":
    st.markdown('<div class="hero"><h1>ECVs</h1><p>Visão consolidada de desempenho por ECV.</p></div>',unsafe_allow_html=True)
    conn=get_connection()
    try:
        ecvs=pd.read_sql_query("""
            SELECT e.id,e.nome,e.cidade,e.estado,e.status,e.meta_mensal,COUNT(v.id) vistorias
            FROM ecvs e LEFT JOIN vistorias v ON v.ecv_id=e.id
            GROUP BY e.id,e.nome,e.cidade,e.estado,e.status,e.meta_mensal
            ORDER BY vistorias DESC
        """,conn)
    finally: conn.close()
    taxa=df.assign(aprovado=df.resultado=="Aprovado").groupby("ecv").aprovado.mean().mul(100).reset_index(name="taxa_aprovacao")
    ecvs=ecvs.merge(taxa,left_on="nome",right_on="ecv",how="left").drop(columns=["ecv"],errors="ignore")
    st.dataframe(ecvs,use_container_width=True,hide_index=True)

else:
    st.markdown('<div class="hero"><h1>API & Integrações</h1><p>Camada REST para integração com sistemas externos e BI.</p></div>',unsafe_allow_html=True)
    for ep in ["GET /health","GET /ecvs","GET /vistorias","GET /indicadores"]: st.code(ep)
    st.code("uvicorn services.api_service:app --reload --port 8000",language="bash")
    st.info("Próxima evolução comercial: autenticação, organization_id, paginação, limites de uso e API keys por cliente.")
