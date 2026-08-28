import os
import json
import pandas as pd

def _local_analysis(kpi, perf):
    worst = perf.sort_values("taxa_aprovacao").iloc[0]
    best = perf.sort_values("taxa_aprovacao", ascending=False).iloc[0]

    return f"""
### 📊 Análise Executiva

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

Investigar os tipos de vistoria e os períodos que concentram reprovações na unidade de menor desempenho. Em um ambiente real, essa análise poderia ser combinada com dados de produtividade, motivos de reprovação e informações de atendimento.

> Esta análise foi gerada pelo modo demonstrativo local. Configure uma API de LLM no ambiente para habilitar respostas generativas.
"""

def _call_llm(prompt):
    # Integração opcional. Para manter o projeto executável sem chave,
    # o app usa análise local quando AI_API_KEY não estiver configurada.
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        return None

    # Exemplo de ponto de integração. Você pode adaptar para o provedor/modelo
    # utilizado pela empresa. Não coloque a chave no GitHub.
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        model = os.getenv("AI_MODEL", "gpt-4.1-mini")
        response = client.responses.create(
            model=model,
            input=prompt,
        )
        return response.output_text
    except Exception:
        return None

def analyze_data(kpi, perf):
    payload = {
        "kpis": kpi,
        "performance": perf.to_dict(orient="records"),
    }
    prompt = f"""
Você é um analista de dados corporativo.
Analise exclusivamente os dados abaixo.
Não invente números. Aponte tendências, anomalias, comparações e recomendações.
Dados:
{json.dumps(payload, ensure_ascii=False, default=str)}
"""
    llm = _call_llm(prompt)
    return llm if llm else _local_analysis(kpi, perf)

def ask_data(question, df):
    q = question.lower()
    perf = df.assign(aprovado=(df["resultado"] == "Aprovado")).groupby("ecv").agg(
        total=("id","count"),
        aprovadas=("aprovado","sum"),
        tempo_medio=("tempo_minutos","mean"),
    ).reset_index()
    perf["taxa"] = perf["aprovadas"] / perf["total"] * 100

    if "pior" in q and ("ecv" in q or "desempenho" in q):
        row = perf.sort_values("taxa").iloc[0]
        return f"**{row['ecv']}** apresentou a menor taxa de aprovação: **{row['taxa']:.1f}%**."

    if "melhor" in q and ("ecv" in q or "desempenho" in q):
        row = perf.sort_values("taxa", ascending=False).iloc[0]
        return f"**{row['ecv']}** apresentou a maior taxa de aprovação: **{row['taxa']:.1f}%**."

    if "quantas" in q or "total" in q:
        return f"O conjunto atual possui **{len(df):,} vistorias**.".replace(",", ".")

    return (
        "Posso responder perguntas básicas sobre os dados, como: "
        "**Qual ECV teve pior desempenho?**, **Qual teve melhor desempenho?** "
        "ou **Quantas vistorias existem?**. Configure `AI_API_KEY` para perguntas generativas."
    )
