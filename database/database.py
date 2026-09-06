"""
ECV Intelligence V3
database/database.py

Camada de acesso ao banco de dados.

Responsabilidades:
- conexão SQLite
- inicialização do schema
- criação do ambiente demo
- seed dos dados demonstrativos
- preparação para arquitetura SaaS multi-tenant
"""

from pathlib import Path
import sqlite3
import random
from datetime import datetime, timedelta


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "ecv_intelligence.db"

SCHEMA_PATH = BASE_DIR / "schema.sql"

DEMO_ORGANIZATION_NAME = "ECV Intelligence Demo"


# ============================================================
# CONEXÃO
# ============================================================

def get_connection():
    """
    Retorna uma conexão SQLite configurada.
    """

    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA foreign_keys = ON")

    return conn


# ============================================================
# EXECUÇÃO DO SCHEMA
# ============================================================

def init_db():
    """
    Inicializa o banco executando o schema.sql.

    CREATE TABLE IF NOT EXISTS permite executar
    esta função várias vezes sem destruir os dados.
    """

    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo schema.sql não encontrado: {SCHEMA_PATH}"
        )

    conn = get_connection()

    try:
        schema = SCHEMA_PATH.read_text(
            encoding="utf-8"
        )

        conn.executescript(schema)
        conn.commit()

    finally:
        conn.close()


# ============================================================
# ORGANIZAÇÃO DEMO
# ============================================================

def _get_or_create_demo_organization(conn):
    """
    Retorna a organização Demo.

    A organização Demo é utilizada exclusivamente
    para os dados de demonstração do produto.
    """

    row = conn.execute(
        """
        SELECT id
        FROM organizations
        WHERE nome = ?
        LIMIT 1
        """,
        (DEMO_ORGANIZATION_NAME,)
    ).fetchone()

    if row:
        return row["id"]

    cursor = conn.execute(
        """
        INSERT INTO organizations
        (
            nome,
            cidade,
            estado,
            status,
            plano
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            DEMO_ORGANIZATION_NAME,
            "São Paulo",
            "SP",
            "ativo",
            "demo"
        )
    )

    return cursor.lastrowid


# ============================================================
# USUÁRIO DEMO
# ============================================================

def _create_demo_users(conn, organization_id):
    """
    Cria usuários demonstrativos somente se não existirem.
    """

    users = [
        (
            "Administrador Demo",
            "admin@ecvintelligence.demo",
            "admin"
        ),
        (
            "Analista Demo",
            "analista@ecvintelligence.demo",
            "analista"
        )
    ]

    for nome, email, perfil in users:

        exists = conn.execute(
            """
            SELECT id
            FROM usuarios
            WHERE organization_id = ?
              AND email = ?
            LIMIT 1
            """,
            (
                organization_id,
                email
            )
        ).fetchone()

        if exists:
            continue

        conn.execute(
            """
            INSERT INTO usuarios
            (
                organization_id,
                nome,
                email,
                perfil,
                ativo
            )
            VALUES (?, ?, ?, ?, 1)
            """,
            (
                organization_id,
                nome,
                email,
                perfil
            )
        )


# ============================================================
# ECVs DEMO
# ============================================================

def _create_demo_ecvs(conn, organization_id):
    """
    Cria as ECVs utilizadas pelo Dashboard demonstrativo.
    """

    ecvs = [
        ("ECV Alpha", "São Paulo", "SP", 50000),
        ("ECV Norte", "Guarulhos", "SP", 45000),
        ("ECV Beta", "Campinas", "SP", 42000),
        ("ECV Centro", "São Paulo", "SP", 48000),
        ("ECV Sul", "Santo André", "SP", 40000),
        ("ECV Oeste", "Osasco", "SP", 38000),
        ("ECV Leste", "Mogi das Cruzes", "SP", 35000),
        ("ECV Interior", "Jundiaí", "SP", 36000),
    ]

    for nome, cidade, estado, meta in ecvs:

        exists = conn.execute(
            """
            SELECT id
            FROM ecvs
            WHERE organization_id = ?
              AND nome = ?
            LIMIT 1
            """,
            (
                organization_id,
                nome
            )
        ).fetchone()

        if exists:
            continue

        conn.execute(
            """
            INSERT INTO ecvs
            (
                organization_id,
                nome,
                cidade,
                estado,
                status,
                meta_mensal
            )
            VALUES (?, ?, ?, ?, 'Ativa', ?)
            """,
            (
                organization_id,
                nome,
                cidade,
                estado,
                meta
            )
        )


# ============================================================
# UNIDADES DEMO
# ============================================================

def _create_demo_unidades(conn, organization_id):
    """
    Cria unidades associadas às ECVs demo.
    """

    ecvs = conn.execute(
        """
        SELECT id, nome, cidade, estado
        FROM ecvs
        WHERE organization_id = ?
        ORDER BY id
        """,
        (organization_id,)
    ).fetchall()

    for ecv in ecvs:

        exists = conn.execute(
            """
            SELECT id
            FROM unidades
            WHERE organization_id = ?
              AND ecv_id = ?
            LIMIT 1
            """,
            (
                organization_id,
                ecv["id"]
            )
        ).fetchone()

        if exists:
            continue

        conn.execute(
            """
            INSERT INTO unidades
            (
                organization_id,
                ecv_id,
                nome,
                cidade,
                estado,
                status
            )
            VALUES (?, ?, ?, ?, ?, 'ativa')
            """,
            (
                organization_id,
                ecv["id"],
                ecv["nome"] + " - Unidade Principal",
                ecv["cidade"],
                ecv["estado"]
            )
        )


# ============================================================
# VISTORIADORES DEMO
# ============================================================

def _create_demo_vistoriadores(conn, organization_id):
    """
    Cria vistoriadores demonstrativos.
    """

    nomes = [
        "Carlos Silva",
        "Marcos Oliveira",
        "João Santos",
        "Rafael Souza",
        "Lucas Pereira",
        "André Costa",
        "Felipe Rodrigues",
        "Bruno Almeida",
        "Diego Martins",
        "Gustavo Lima",
    ]

    ecvs = conn.execute(
        """
        SELECT id
        FROM ecvs
        WHERE organization_id = ?
        ORDER BY id
        """,
        (organization_id,)
    ).fetchall()

    existing = conn.execute(
        """
        SELECT COUNT(*)
        FROM vistoriadores
        WHERE organization_id = ?
        """,
        (organization_id,)
    ).fetchone()[0]

    if existing > 0:
        return

    for index, nome in enumerate(nomes):

        ecv_id = ecvs[
            index % len(ecvs)
        ]["id"] if ecvs else None

        conn.execute(
            """
            INSERT INTO vistoriadores
            (
                organization_id,
                ecv_id,
                nome,
                matricula,
                status
            )
            VALUES (?, ?, ?, ?, 'ativo')
            """,
            (
                organization_id,
                ecv_id,
                nome,
                f"VST-{1000 + index}"
            )
        )


# ============================================================
# VISTORIAS DEMO
# ============================================================

def _create_demo_vistorias(conn, organization_id, total=5000):
    """
    Cria os registros demonstrativos.

    Importante:
    - somente cria registros se ainda não houver vistorias
    - todos os registros pertencem à organização Demo
    """

    existing = conn.execute(
        """
        SELECT COUNT(*)
        FROM vistorias
        WHERE organization_id = ?
        """,
        (organization_id,)
    ).fetchone()[0]

    if existing > 0:
        return

    ecvs = conn.execute(
        """
        SELECT id
        FROM ecvs
        WHERE organization_id = ?
        ORDER BY id
        """,
        (organization_id,)
    ).fetchall()

    unidades = conn.execute(
        """
        SELECT id, ecv_id
        FROM unidades
        WHERE organization_id = ?
        ORDER BY id
        """,
        (organization_id,)
    ).fetchall()

    vistoriadores = conn.execute(
        """
        SELECT id, ecv_id
        FROM vistoriadores
        WHERE organization_id = ?
        ORDER BY id
        """,
        (organization_id,)
    ).fetchall()

    if not ecvs:
        return

    random.seed(42)

    tipos = [
        "Cautelar",
        "Transferência",
        "Identificação",
        "Completa",
    ]

    resultados = [
        "Aprovado",
        "Aprovado",
        "Aprovado",
        "Reprovado",
    ]

    hoje = datetime.now()

    registros = []

    for i in range(total):

        ecv = random.choice(ecvs)

        ecv_id = ecv["id"]

        unidade_id = None

        unidades_ecv = [
            u for u in unidades
            if u["ecv_id"] == ecv_id
        ]

        if unidades_ecv:
            unidade_id = random.choice(
                unidades_ecv
            )["id"]

        vistoriador_id = None

        vistoriadores_ecv = [
            v for v in vistoriadores
            if v["ecv_id"] == ecv_id
        ]

        if vistoriadores_ecv:
            vistoriador_id = random.choice(
                vistoriadores_ecv
            )["id"]

        data = hoje - timedelta(
            days=random.randint(0, 59),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )

        placa = (
            f"{chr(65 + random.randint(0, 25))}"
            f"{chr(65 + random.randint(0, 25))}"
            f"{chr(65 + random.randint(0, 25))}-"
            f"{random.randint(1000, 9999)}"
        )

        tipo = random.choice(tipos)

        resultado = random.choice(resultados)

        tempo = round(
            random.uniform(12, 45),
            1
        )

        valor = round(
            random.uniform(80, 180),
            2
        )

        registros.append(
            (
                organization_id,
                ecv_id,
                unidade_id,
                vistoriador_id,
                placa,
                tipo,
                data.strftime("%Y-%m-%d %H:%M:%S"),
                resultado,
                tempo,
                valor,
            )
        )

    conn.executemany(
        """
        INSERT INTO vistorias
        (
            organization_id,
            ecv_id,
            unidade_id,
            vistoriador_id,
            placa,
            tipo,
            data_vistoria,
            resultado,
            tempo_minutos,
            valor
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        registros
    )


# ============================================================
# AUTOMAÇÕES DEMO
# ============================================================

def _create_demo_automation(conn, organization_id):

    exists = conn.execute(
        """
        SELECT id
        FROM automation_rules
        WHERE organization_id = ?
        LIMIT 1
        """,
        (organization_id,)
    ).fetchone()

    if exists:
        return

    conn.execute(
        """
        INSERT INTO automation_rules
        (
            organization_id,
            nome,
            descricao,
            tipo,
            condicao,
            acao,
            ativo
        )
        VALUES (?, ?, ?, ?, ?, ?, 1)
        """,
        (
            organization_id,
            "Monitoramento de qualidade",
            "Detecta inconsistências nos dados das vistorias.",
            "qualidade",
            "dados_invalidos > 0",
            "gerar_alerta"
        )
    )


# ============================================================
# SEED PRINCIPAL
# ============================================================

def seed_database():
    """
    Inicializa o ambiente demonstrativo.

    A função é idempotente:
    pode ser chamada várias vezes sem duplicar
    os 5.000 registros.
    """

    conn = get_connection()

    try:

        organization_id = _get_or_create_demo_organization(
            conn
        )

        _create_demo_users(
            conn,
            organization_id
        )

        _create_demo_ecvs(
            conn,
            organization_id
        )

        _create_demo_unidades(
            conn,
            organization_id
        )

        _create_demo_vistoriadores(
            conn,
            organization_id
        )

        _create_demo_vistorias(
            conn,
            organization_id,
            total=5000
        )

        _create_demo_automation(
            conn,
            organization_id
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# ============================================================
# INFORMAÇÕES DO BANCO
# ============================================================

def get_database_stats():
    """
    Retorna estatísticas básicas do banco.
    """

    conn = get_connection()

    try:

        stats = {}

        tables = [
            "organizations",
            "usuarios",
            "ecvs",
            "unidades",
            "vistoriadores",
            "vistorias",
            "automation_rules",
            "logs_automacao",
            "ai_insights",
            "alerts",
            "audit_logs",
            "plans",
            "subscriptions",
        ]

        for table in tables:

            row = conn.execute(
                f"SELECT COUNT(*) AS total FROM {table}"
            ).fetchone()

            stats[table] = row["total"]

        return stats

    finally:
        conn.close()


# ============================================================
# BOOTSTRAP
# ============================================================

def bootstrap_database():
    """
    Inicializa o schema e cria os dados Demo.

    Esta função será utilizada futuramente pelo app.py.
    """

    init_db()
    seed_database()


# ============================================================
# EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":

    print("Inicializando ECV Intelligence V3...")

    bootstrap_database()

    stats = get_database_stats()

    print("\nBanco inicializado com sucesso.\n")

    for table, total in stats.items():
        print(f"{table}: {total}")
