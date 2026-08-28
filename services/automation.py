from datetime import datetime
from database.database import get_connection

def run_pipeline():
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM vistorias").fetchone()[0]
        duplicate_rows = conn.execute("""
            SELECT COUNT(*) FROM (
                SELECT placa, data_vistoria, ecv_id, COUNT(*) c
                FROM vistorias
                GROUP BY placa, data_vistoria, ecv_id
                HAVING c > 1
            )
        """).fetchone()[0]

        issues = conn.execute("""
            SELECT COUNT(*) FROM vistorias
            WHERE tempo_minutos <= 0 OR valor <= 0 OR placa IS NULL OR data_vistoria IS NULL
        """).fetchone()[0]

        steps = [
            "Leitura dos dados no SQLite",
            "Validação de registros",
            "Verificação de duplicidades",
            "Validação de campos críticos",
            "Atualização dos indicadores",
            "Registro da execução",
        ]

        conn.execute("""
            INSERT INTO logs_automacao
            (processo, status, registros_processados, mensagem)
            VALUES (?,?,?,?,?)
        """, (
            "Pipeline de Dados",
            "Concluído",
            total,
            f"Duplicidades potenciais: {duplicate_rows}; inconsistências: {issues}"
        ))
        conn.commit()

        return {
            "status": "success",
            "processed": total,
            "duplicates": duplicate_rows,
            "issues": issues,
            "steps": steps,
        }
    except Exception as exc:
        conn.execute("""
            INSERT INTO logs_automacao
            (processo, status, registros_processados, mensagem)
            VALUES (?,?,?,?,?)
        """, ("Pipeline de Dados", "Erro", 0, str(exc)))
        conn.commit()
        return {"status": "error", "message": str(exc)}
    finally:
        conn.close()
