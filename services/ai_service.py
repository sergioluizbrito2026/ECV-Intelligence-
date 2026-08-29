import json
import os
import pandas as pd
from google import genai
import streamlit as st



def _get_gemini_client():
  # Tenta pegar a chave do Streamlit Secrets ou das variáveis de ambiente
  api_key = (
      st.secrets.get("GEMINI_API_KEY")
      if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets
      else os.getenv("GEMINI_API_KEY")
  )
  if not api_key:
    return None
  return genai.Client(api_key=api_key)


def analyze_data(kpi, perf):
  client = _get_gemini_client()

  # Payload com os dados para a IA analisar
  payload = {
      "kpis": kpi,
      "performance": perf.to_dict(orient="records"),
  }

  prompt = f"""
Você é um Analista de Dados Sênior e especialista em operações de ECVs (Empresas Credenciadas de Vistoria).
Analise exclusivamente os dados abaixo. Não invente números. 
Gere uma Análise Executiva profissional e direta em Markdown, contendo:
- 📊 **Visão Geral:** Métricas principais de volume, aprovação, reprovação e faturamento.
- 🔍 **Destaques:** Unidades com melhor e pior desempenho operacional e suas diferenças.
- 💡 **Recomendação Estratégica:** Uma recomendação prática para a gestão.

Dados operacionais:
{json.dumps(payload, ensure_ascii=False, default=str)}

Importante: Seja objetivo, profissional e não inclua nenhum aviso de rodapé ou menção a modo demonstrativo.
"""

  if client:
    try:
      response = client.models.generate_content(
          model="gemini-2.5-flash", contents=prompt
      )
      if response and response.text:
        return response.text
    except Exception as e:
      # Se falhar a API, cai no fallback local abaixo para nunca quebrar a aplicação
      pass

  # Fallback local profissional caso a chave não esteja ativa
  worst = perf.sort_values("taxa_aprovacao").iloc[0]
  best = perf.sort_values("taxa_aprovacao", ascending=False).iloc[0]

  return f"""### 📊 Análise Executiva

Foram analisadas **{kpi['total']:,} vistorias** no período disponível.

- **Taxa de aprovação:** {kpi['taxa_aprovacao']:.1f}%
- **Taxa de reprovação:** {kpi['taxa_reprovacao']:.1f}%
- **Tempo médio:** {kpi['tempo_medio']:.1f} minutos
- **Faturamento:** R$ {kpi['faturamento']:,.2f}

### 🔎 Destaques

- Melhor taxa de aprovação: **{best['ecv']} ({best['taxa_aprovacao']:.1f}%)**
- Menor taxa de aprovação: **{worst['ecv']} ({worst['taxa_aprovacao']:.1f}%)**
- Diferença entre as unidades de melhor e pior desempenho: **{best['taxa_aprovacao'] - worst['taxa_aprovacao']:.1f} p.p.**

### 💡 Recomendação

Investigar os tipos de vistoria e os períodos que concentram reprovações na unidade de menor desempenho. Combinar com dados de produtividade e motivos de reprovação para otimizar o fluxo operacional.
"""


def ask_data(question, df):
  client = _get_gemini_client()

  # Se o cliente Gemini estiver ativo, deixa a IA responder livremente baseada nos dados do DataFrame
  if client:
    try:
      resumo_amostra = (
          df.head(60).to_string() if len(df) > 60 else df.to_string()
      )
      prompt = f"""
Você é o Copilot de inteligência de dados de um sistema de gestão de ECVs.
Com base nesta amostra recente da base de dados operacionais:
{resumo_amostra}

Responda à pergunta do usuário de forma clara, analítica e direta:
Pergunta: "{question}"
"""
      response = client.models.generate_content(
          model="gemini-2.5-flash", contents=prompt
      )
      if response and response.text:
        return response.text
    except Exception:
      pass

  # Fallback local inteligente caso a IA não seja acionada
  q = question.lower()
  perf = (
      df.assign(aprovado=(df["resultado"] == "Aprovado"))
      .groupby("ecv")
      .agg(
          total=("id", "count"),
          aprovadas=("aprovado", "sum"),
          tempo_medio=("tempo_minutos", "mean"),
      )
      .reset_index()
  )
  perf["taxa"] = perf["aprovadas"] / perf["total"] * 100

  if "pior" in q and ("ecv" in q or "desempenho" in q or "reprovação" in q):
    row = perf.sort_values("taxa").iloc[0]
    return f"**{row['ecv']}** apresentou a menor taxa de aprovação da base: **{row['taxa']:.1f}%**."

  if "melhor" in q and ("ecv" in q or "desempenho" in q or "aprovação" in q):
    row = perf.sort_values("taxa", ascending=False).iloc[0]
    return f"**{row['ecv']}** apresentou a maior taxa de aprovação da base: **{row['taxa']:.1f}%**."

  if "quantas" in q or "total" in q:
    return f"O conjunto atual possui **{len(df):,} vistorias**.".replace(
        ",", "."
    )

  return (
      "Posso responder perguntas operacionais sobre os dados, como: "
      "**Qual ECV teve pior desempenho?**, **Qual teve melhor desempenho?** "
      "ou **Quantas vistorias existem?**."
  )
