# 🚗 ECV Intelligence V2

### Plataforma profissional de Automação, Business Intelligence e Inteligência Artificial para Gestão de Vistorias

O **ECV Intelligence** é um projeto demonstrativo desenvolvido para explorar a aplicação de **Dados, Business Intelligence, Automação e Inteligência Artificial** em operações de Empresas Credenciadas de Vistoria (ECVs).

A solução transforma dados operacionais em indicadores, análises e insights para apoiar processos de tomada de decisão.

> ⚠️ **Dados fictícios:** este projeto não utiliza informações reais de clientes, veículos ou empresas.

## 🎯 Objetivo

Demonstrar uma solução que:

- trata e valida dados;
- utiliza SQL e SQLite;
- cria indicadores;
- apresenta dashboards;
- automatiza tarefas;
- integra uma API REST;
- utiliza IA para análise;
- prepara dados para Power BI;
- identifica oportunidades de melhoria.

## 🧠 Funcionalidades

### 📊 Dashboard
- total de vistorias;
- taxa de aprovação;
- taxa de reprovação;
- tempo médio;
- faturamento;
- performance por ECV;
- evolução diária.

### 🧹 Qualidade dos Dados
- duplicidades;
- valores vazios;
- placas fora do padrão;
- validações básicas.

### ⚙️ Automação
Pipeline:

```text
Importação
   ↓
Validação
   ↓
Tratamento
   ↓
SQLite
   ↓
KPIs
   ↓
IA
   ↓
Log
```

### 🤖 Inteligência Artificial

A solução possui dois modos:

1. **Modo local:** funciona sem API e gera análises determinísticas baseadas nos dados.
2. **Modo generativo:** quando `AI_API_KEY` está configurada, utiliza um modelo LLM para gerar análise em linguagem natural.

A IA recebe os indicadores disponíveis e possui regras para não inventar números.

### 🔌 API

Endpoints:

```text
GET /health
GET /ecvs
GET /vistorias
GET /indicadores
```

## 🏗️ Arquitetura

```text
                 STREAMLIT
                     │
       ┌─────────────┼─────────────┐
       │             │             │
     Dados       Automação         IA
       │             │             │
       └─────────────┼─────────────┘
                     │
                  SQLite
                     │
                  KPIs
                     │
                 Power BI
```

## 🛠️ Tecnologias

- Python
- Streamlit
- Pandas
- SQLite
- SQL
- Plotly
- FastAPI
- Power BI
- Power Query
- DAX
- REST API
- IA Generativa
- AI Coding
- Git/GitHub

## 📁 Estrutura

```text
ecv-intelligence/
├── app.py
├── requirements.txt
├── README.md
├── .env.example
├── database/
│   ├── database.py
│   └── schema.sql
├── data/
│   └── generate_data.py
├── services/
│   ├── analytics.py
│   ├── automation.py
│   ├── ai_service.py
│   └── api_service.py
├── powerbi/
│   ├── README.md
│   └── queries.sql
└── docs/
    └── arquitetura.md
```

## 🚀 Como executar

### 1. Clonar

```bash
git clone https://github.com/SEU-USUARIO/ecv-intelligence.git
cd ecv-intelligence
```

### 2. Criar ambiente virtual

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Executar

```bash
streamlit run app.py
```

Na primeira execução, o sistema cria o banco SQLite e gera 5.000 registros fictícios.

## 🤖 Configurar IA generativa

Copie:

```text
.env.example
```

para:

```text
.env
```

e preencha sua chave.

```text
AI_API_KEY=sua_chave
AI_MODEL=gpt-4.1-mini
```

**Nunca envie `.env` para o GitHub.**

## 🔌 Executar API

Em outro terminal:

```bash
uvicorn services.api_service:app --reload --port 8000
```

Documentação automática:

```text
http://127.0.0.1:8000/docs
```

## 📈 Power BI

O diretório `powerbi/` contém consultas SQL e medidas DAX sugeridas.

Principais medidas:

```DAX
Total Vistorias =
COUNTROWS(Vistorias)

Vistorias Aprovadas =
CALCULATE(
    [Total Vistorias],
    Vistorias[resultado] = "Aprovado"
)

Taxa Aprovação =
DIVIDE(
    [Vistorias Aprovadas],
    [Total Vistorias],
    0
)
```

## 🤖 AI Coding

Durante o desenvolvimento, ferramentas de Inteligência Artificial podem ser utilizadas como apoio para:

- geração e revisão de código;
- criação de consultas SQL;
- debugging;
- documentação;
- criação rápida de protótipos;
- desenvolvimento de funções;
- melhoria da arquitetura.

A validação das regras, dos resultados e da integração deve permanecer sob responsabilidade do desenvolvedor.

## 💼 Aplicação empresarial

Em um cenário real, a arquitetura poderia ser adaptada para:

- monitoramento operacional;
- produtividade;
- controle de indicadores;
- análise de qualidade;
- automação de relatórios;
- integração de sistemas;
- detecção de anomalias;
- apoio à tomada de decisão.

## ⚠️ Disclaimer

Este é um projeto de portfólio. Todos os dados são simulados.

## 👩‍💻 Autora

**Larissa Mendes Brito**

**Data Analytics | Business Intelligence | Python | SQL | Power BI | Inteligência Artificial | Automação**


## ✨ V2 — Interface profissional

A segunda versão adiciona:

- interface SaaS mais limpa e responsiva;
- navegação por áreas de negócio;
- visão executiva com KPIs;
- cards de performance;
- área dedicada a qualidade dos dados;
- central de automações;
- área de IA e insights;
- documentação visual de API;
- separação entre camada de interface, dados, serviços e analytics.

O objetivo da V2 é aproximar o projeto de um **protótipo interno corporativo**, mantendo a simplicidade necessária para um projeto de portfólio.
