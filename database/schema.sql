CREATE TABLE IF NOT EXISTS ecvs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    cidade TEXT NOT NULL,
    estado TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Ativa',
    meta_mensal INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS vistorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ecv_id INTEGER NOT NULL,
    placa TEXT NOT NULL,
    tipo_vistoria TEXT NOT NULL,
    data_vistoria DATE NOT NULL,
    resultado TEXT NOT NULL,
    tempo_minutos REAL NOT NULL,
    valor REAL NOT NULL,
    FOREIGN KEY (ecv_id) REFERENCES ecvs(id)
);

CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    perfil TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS logs_automacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    processo TEXT NOT NULL,
    executado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL,
    registros_processados INTEGER DEFAULT 0,
    mensagem TEXT
);
