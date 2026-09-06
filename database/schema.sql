PRAGMA foreign_keys = ON;

-- ============================================================
-- ECV INTELLIGENCE V3
-- Schema SaaS Multi-Tenant
-- ============================================================

-- ============================================================
-- 1. ORGANIZAÇÕES / CLIENTES
-- ============================================================

CREATE TABLE IF NOT EXISTS organizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    nome TEXT NOT NULL,
    cnpj TEXT UNIQUE,

    cidade TEXT,
    estado TEXT,

    status TEXT NOT NULL DEFAULT 'ativo'
        CHECK (status IN ('ativo', 'inativo', 'trial', 'suspenso')),

    plano TEXT NOT NULL DEFAULT 'starter'
        CHECK (plano IN (
            'demo',
            'starter',
            'professional',
            'business',
            'enterprise'
        )),

    trial_inicio TEXT,
    trial_fim TEXT,

    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- 2. USUÁRIOS
-- ============================================================

CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    organization_id INTEGER NOT NULL,

    nome TEXT NOT NULL,
    email TEXT NOT NULL,
    senha_hash TEXT,

    perfil TEXT NOT NULL DEFAULT 'analista'
        CHECK (perfil IN (
            'owner',
            'admin',
            'gestor',
            'supervisor',
            'analista',
            'vistoriador'
        )),

    ativo INTEGER NOT NULL DEFAULT 1
        CHECK (ativo IN (0,1)),

    ultimo_login TEXT,

    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (organization_id)
        REFERENCES organizations(id)
        ON DELETE CASCADE,

    UNIQUE (organization_id, email)
);


-- ============================================================
-- 3. ECVs
-- ============================================================

CREATE TABLE IF NOT EXISTS ecvs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    organization_id INTEGER NOT NULL,

    nome TEXT NOT NULL,
    cidade TEXT,
    estado TEXT,

    status TEXT NOT NULL DEFAULT 'Ativa',

    meta_mensal REAL NOT NULL DEFAULT 0,

    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (organization_id)
        REFERENCES organizations(id)
        ON DELETE CASCADE
);


-- ============================================================
-- 4. UNIDADES
-- ============================================================

CREATE TABLE IF NOT EXISTS unidades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    organization_id INTEGER NOT NULL,
    ecv_id INTEGER NOT NULL,

    nome TEXT NOT NULL,

    cidade TEXT,
    estado TEXT,

    endereco TEXT,

    status TEXT NOT NULL DEFAULT 'ativa'
        CHECK (status IN ('ativa', 'inativa')),

    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (organization_id)
        REFERENCES organizations(id)
        ON DELETE CASCADE,

    FOREIGN KEY (ecv_id)
        REFERENCES ecvs(id)
        ON DELETE CASCADE
);


-- ============================================================
-- 5. VISTORIADORES
-- ============================================================

CREATE TABLE IF NOT EXISTS vistoriadores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    organization_id INTEGER NOT NULL,
    ecv_id INTEGER,

    nome TEXT NOT NULL,
    email TEXT,

    matricula TEXT,

    status TEXT NOT NULL DEFAULT 'ativo'
        CHECK (status IN ('ativo', 'inativo')),

    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (organization_id)
        REFERENCES organizations(id)
        ON DELETE CASCADE,

    FOREIGN KEY (ecv_id)
        REFERENCES ecvs(id)
        ON DELETE SET NULL
);


-- ============================================================
-- 6. VISTORIAS
-- ============================================================

CREATE TABLE IF NOT EXISTS vistorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    organization_id INTEGER NOT NULL,

    ecv_id INTEGER NOT NULL,
    unidade_id INTEGER,
    vistoriador_id INTEGER,

    placa TEXT NOT NULL,

    tipo TEXT NOT NULL,

    data_vistoria TEXT NOT NULL,

    resultado TEXT NOT NULL,

    tempo_minutos REAL NOT NULL DEFAULT 0,

    valor REAL NOT NULL DEFAULT 0,

    observacoes TEXT,

    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (organization_id)
        REFERENCES organizations(id)
        ON DELETE CASCADE,

    FOREIGN KEY (ecv_id)
        REFERENCES ecvs(id)
        ON DELETE CASCADE,

    FOREIGN KEY (unidade_id)
        REFERENCES unidades(id)
        ON DELETE SET NULL,

    FOREIGN KEY (vistoriador_id)
        REFERENCES vistoriadores(id)
        ON DELETE SET NULL
);


-- ============================================================
-- 7. REGRAS DE AUTOMAÇÃO
-- ============================================================

CREATE TABLE IF NOT EXISTS automation_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    organization_id INTEGER NOT NULL,

    nome TEXT NOT NULL,
    descricao TEXT,

    tipo TEXT NOT NULL,

    condicao TEXT NOT NULL,

    acao TEXT NOT NULL,

    ativo INTEGER NOT NULL DEFAULT 1
        CHECK (ativo IN (0,1)),

    cooldown_minutos INTEGER DEFAULT 60,

    criado_por INTEGER,

    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (organization_id)
        REFERENCES organizations(id)
        ON DELETE CASCADE,

    FOREIGN KEY (criado_por)
        REFERENCES usuarios(id)
        ON DELETE SET NULL
);


-- ============================================================
-- 8. LOGS DE AUTOMAÇÃO
-- ============================================================

CREATE TABLE IF NOT EXISTS logs_automacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    organization_id INTEGER NOT NULL,

    regra_id INTEGER,

    processo TEXT NOT NULL,

    executado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    status TEXT NOT NULL,

    registros_processados INTEGER DEFAULT 0,

    duracao_ms INTEGER,

    mensagem TEXT,

    FOREIGN KEY (organization_id)
        REFERENCES organizations(id)
        ON DELETE CASCADE,

    FOREIGN KEY (regra_id)
        REFERENCES automation_rules(id)
        ON DELETE SET NULL
);


-- ============================================================
-- 9. INSIGHTS DA IA
-- ============================================================

CREATE TABLE IF NOT EXISTS ai_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    organization_id INTEGER NOT NULL,

    tipo TEXT NOT NULL,

    titulo TEXT NOT NULL,

    descricao TEXT NOT NULL,

    prioridade TEXT DEFAULT 'media'
        CHECK (prioridade IN (
            'baixa',
            'media',
            'alta',
            'critica'
        )),

    origem TEXT DEFAULT 'ia',

    dados_contexto TEXT,

    status TEXT DEFAULT 'novo'
        CHECK (status IN (
            'novo',
            'visualizado',
            'resolvido',
            'ignorado'
        )),

    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (organization_id)
        REFERENCES organizations(id)
        ON DELETE CASCADE
);


-- ============================================================
-- 10. ALERTAS
-- ============================================================

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    organization_id INTEGER NOT NULL,

    tipo TEXT NOT NULL,

    titulo TEXT NOT NULL,

    mensagem TEXT NOT NULL,

    prioridade TEXT DEFAULT 'media'
        CHECK (prioridade IN (
            'baixa',
            'media',
            'alta',
            'critica'
        )),

    status TEXT DEFAULT 'novo'
        CHECK (status IN (
            'novo',
            'lido',
            'resolvido'
        )),

    usuario_id INTEGER,

    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolvido_em TEXT,

    FOREIGN KEY (organization_id)
        REFERENCES organizations(id)
        ON DELETE CASCADE,

    FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
        ON DELETE SET NULL
);


-- ============================================================
-- 11. AUDITORIA
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    organization_id INTEGER NOT NULL,

    usuario_id INTEGER,

    acao TEXT NOT NULL,

    entidade TEXT,

    entidade_id INTEGER,

    detalhes TEXT,

    ip_address TEXT,

    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (organization_id)
        REFERENCES organizations(id)
        ON DELETE CASCADE,

    FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
        ON DELETE SET NULL
);


-- ============================================================
-- 12. PLANOS
-- ============================================================

CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    nome TEXT NOT NULL UNIQUE,

    descricao TEXT,

    preco_mensal REAL NOT NULL DEFAULT 0,

    limite_usuarios INTEGER,
    limite_ecvs INTEGER,
    limite_vistorias INTEGER,

    recursos TEXT,

    ativo INTEGER NOT NULL DEFAULT 1
        CHECK (ativo IN (0,1)),

    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- 13. ASSINATURAS
-- ============================================================

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    organization_id INTEGER NOT NULL,

    plan_id INTEGER NOT NULL,

    status TEXT NOT NULL DEFAULT 'trial'
        CHECK (status IN (
            'trial',
            'active',
            'past_due',
            'cancelled',
            'expired'
        )),

    inicio TEXT,
    fim TEXT,

    external_customer_id TEXT,
    external_subscription_id TEXT,

    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (organization_id)
        REFERENCES organizations(id)
        ON DELETE CASCADE,

    FOREIGN KEY (plan_id)
        REFERENCES plans(id)
        ON DELETE RESTRICT
);


-- ============================================================
-- ÍNDICES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_users_organization
ON usuarios(organization_id);

CREATE INDEX IF NOT EXISTS idx_ecvs_organization
ON ecvs(organization_id);

CREATE INDEX IF NOT EXISTS idx_unidades_organization
ON unidades(organization_id);

CREATE INDEX IF NOT EXISTS idx_vistoriadores_organization
ON vistoriadores(organization_id);

CREATE INDEX IF NOT EXISTS idx_vistorias_organization
ON vistorias(organization_id);

CREATE INDEX IF NOT EXISTS idx_vistorias_ecv
ON vistorias(ecv_id);

CREATE INDEX IF NOT EXISTS idx_vistorias_data
ON vistorias(data_vistoria);

CREATE INDEX IF NOT EXISTS idx_vistorias_resultado
ON vistorias(resultado);

CREATE INDEX IF NOT EXISTS idx_automation_organization
ON automation_rules(organization_id);

CREATE INDEX IF NOT EXISTS idx_logs_automation_organization
ON logs_automacao(organization_id);

CREATE INDEX IF NOT EXISTS idx_ai_insights_organization
ON ai_insights(organization_id);

CREATE INDEX IF NOT EXISTS idx_alerts_organization
ON alerts(organization_id);

CREATE INDEX IF NOT EXISTS idx_audit_organization
ON audit_logs(organization_id);

CREATE INDEX IF NOT EXISTS idx_subscription_organization
ON subscriptions(organization_id);


-- ============================================================
-- PLANOS INICIAIS
-- ============================================================

INSERT OR IGNORE INTO plans
    (nome, descricao, preco_mensal, limite_usuarios, limite_ecvs, limite_vistorias, recursos)
VALUES
    (
        'demo',
        'Ambiente demonstrativo',
        0,
        3,
        10,
        5000,
        'Dashboard, Vistorias, Qualidade, IA'
    ),
    (
        'starter',
        'Plano inicial',
        149,
        3,
        1,
        5000,
        'Dashboard, Vistorias, Indicadores'
    ),
    (
        'professional',
        'Plano profissional',
        349,
        10,
        10,
        25000,
        'Dashboard, IA, Alertas, Relatórios, Automações'
    ),
    (
        'business',
        'Plano empresarial',
        799,
        30,
        50,
        100000,
        'IA, API, Power BI, Automações, Auditoria'
    ),
    (
        'enterprise',
        'Plano personalizado',
        0,
        NULL,
        NULL,
        NULL,
        'Recursos personalizados e integrações'
    );
