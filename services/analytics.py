import pandas as pd

def get_kpis(df):
    total = len(df)
    approved = int((df["resultado"] == "Aprovado").sum())
    rejected = int((df["resultado"] == "Reprovado").sum())
    return {
        "total": total,
        "aprovadas": approved,
        "reprovadas": rejected,
        "taxa_aprovacao": approved / total * 100 if total else 0,
        "taxa_reprovacao": rejected / total * 100 if total else 0,
        "tempo_medio": float(df["tempo_minutos"].mean()) if total else 0,
        "faturamento": float(df["valor"].sum()) if total else 0,
    }

def get_daily_series(df):
    result = (
        df.assign(data=pd.to_datetime(df["data_vistoria"]).dt.date)
        .groupby("data")
        .size()
        .reset_index(name="vistorias")
    )
    return result

def get_ecv_performance(df):
    result = df.assign(aprovado=(df["resultado"] == "Aprovado")).groupby("ecv").agg(
        total=("id", "count"),
        aprovadas=("aprovado", "sum"),
        tempo_medio=("tempo_minutos", "mean"),
    ).reset_index()
    result["taxa_aprovacao"] = result["aprovadas"] / result["total"] * 100
    return result.sort_values("taxa_aprovacao", ascending=False)

def get_quality_report(df):
    dup = int(df.duplicated(subset=["placa", "data_vistoria", "ecv"]).sum())
    nulls = int(df.isna().sum().sum())
    invalid_plates = int((~df["placa"].astype(str).str.match(r"^[A-Z]{3}-\d{4}$")).sum())
    messages = [
        f"🔎 Foram analisados {len(df):,} registros.".replace(",", "."),
        f"🔁 Duplicidades potenciais: {dup}.",
        f"⬜ Campos vazios: {nulls}.",
        f"🚘 Placas fora do padrão esperado: {invalid_plates}.",
        "💡 Em uma operação real, regras adicionais poderiam validar datas, valores, integridade referencial e consistência entre sistemas.",
    ]
    return {
        "total": len(df),
        "duplicados": dup,
        "nulos": nulls,
        "placas_invalidas": invalid_plates,
        "mensagens": messages,
    }
