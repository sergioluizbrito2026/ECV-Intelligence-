# 🚗 ECV Intelligence

### Plataforma de Automação, Business Intelligence e Inteligência Artificial para Gestão de Vistorias

O **ECV Intelligence** é um projeto demonstrativo desenvolvido para explorar a aplicação de **Dados, Business Intelligence, Automação e Inteligência Artificial** em operações de Empresas Credenciadas de Vistoria (ECVs).

A solução transforma dados operacionais em indicadores, análises e insights para apoiar processos de tomada de decisão.

> ⚠️ **Aviso:** este projeto utiliza dados fictícios e foi desenvolvido exclusivamente para fins educacionais e demonstrativos.

---

## 🎯 Objetivo

Demonstrar como tecnologias de dados e Inteligência Artificial podem ser utilizadas para:

* automatizar tarefas manuais;
* tratar e validar dados;
* centralizar informações;
* criar indicadores operacionais;
* acompanhar KPIs;
* identificar inconsistências;
* analisar desempenho;
* integrar diferentes fontes de dados;
* gerar insights utilizando IA;
* apoiar a tomada de decisão.

---

## 🧠 Principais funcionalidades

### 📊 Dashboard Executivo

Apresenta indicadores como:

* total de vistorias;
* taxa de aprovação;
* taxa de reprovação;
* tempo médio de atendimento;
* faturamento;
* desempenho por ECV;
* evolução das vistorias.

### 🧹 Qualidade dos Dados

O sistema identifica:

* registros duplicados;
* campos vazios;
* datas inválidas;
* inconsistências;
* problemas de padronização.

### ⚙️ Automação

Pipeline automatizado para:

```text
Importação
    ↓
Validação
    ↓
Tratamento
    ↓
Persistência
    ↓
Cálculo de indicadores
    ↓
Análise
    ↓
Relatório
```

### 🤖 Inteligência Artificial

A IA é utilizada para analisar indicadores e gerar interpretações baseadas exclusivamente nos dados disponibilizados pelo sistema.

Exemplos:

* identificação de tendências;
* comparação de desempenho;
* identificação de anomalias;
* geração de recomendações;
* análise executiva.

### 💬 Pergunte aos Dados

Permite realizar perguntas em linguagem natural sobre os indicadores disponíveis.

Exemplo:

> "Qual ECV apresentou o maior índice de reprovação?"

---

## 🏗️ Arquitetura

```text
                    Streamlit
                       │
        ┌──────────────┼──────────────┐
        │              │              │
      Dados        Automação          IA
        │              │              │
        └──────────────┼──────────────┘
                       │
                    SQLite
                       │
                  Indicadores
                       │
                    Power BI
```

---

## 🛠️ Tecnologias

| Tecnologia    | Utilização            |
| ------------- | --------------------- |
| Python        | Desenvolvimento       |
| Streamlit     | Interface             |
| Pandas        | Tratamento de dados   |
| SQLite        | Banco de dados        |
| SQL           | Consultas             |
| Plotly        | Visualizações         |
| Power BI      | Business Intelligence |
| Power Query   | ETL                   |
| DAX           | Indicadores           |
| REST API      | Integrações           |
| IA Generativa | Análise e automação   |
| Git/GitHub    | Versionamento         |

---

## 📁 Estrutura

```text
ecv-intelligence/
│
├── app.py
├── requirements.txt
├── README.md
├── .env.example
│
├── database/
├── data/
├── services/
├── pages/
├── utils/
├── powerbi/
└── docs/
```

---

## 🚀 Como executar

Clone o projeto:

```bash
git clone https://github.com/seu-usuario/ecv-intelligence.git
```

Entre na pasta:

```bash
cd ecv-intelligence
```

Crie um ambiente virtual:

```bash
python -m venv .venv
```

Ative o ambiente:

### Windows

```bash
.venv\Scripts\activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Execute:

```bash
streamlit run app.py
```

---

## 🔐 Configuração da IA

As credenciais da API devem ser armazenadas em variáveis de ambiente.

Exemplo:

```text
AI_API_KEY=sua_chave
AI_MODEL=seu_modelo
```

Nunca armazene chaves de API diretamente no código ou no GitHub.

---

## 📈 Exemplo de fluxo

```text
Arquivo CSV/Excel
       ↓
Validação
       ↓
Tratamento
       ↓
SQLite
       ↓
SQL
       ↓
KPIs
       ↓
Power BI
       ↓
IA
       ↓
Insights
       ↓
Tomada de decisão
```

---

## 🤖 Uso de AI Coding

Durante o desenvolvimento, ferramentas de Inteligência Artificial foram utilizadas como apoio para:

* geração e revisão de código;
* criação de consultas SQL;
* identificação de erros;
* documentação;
* criação de protótipos;
* elaboração de funções;
* melhoria da estrutura do projeto.

A validação das regras de negócio, dos resultados e da integração entre os componentes foi realizada durante o desenvolvimento do projeto.

---

## 🔎 Possíveis aplicações empresariais

A arquitetura pode ser adaptada para diferentes cenários, como:

* acompanhamento operacional;
* análise de produtividade;
* controle de indicadores;
* monitoramento de unidades;
* análise de qualidade;
* automação de relatórios;
* integração entre sistemas;
* identificação de anomalias.

---

## 📚 Objetivo profissional

Este projeto foi desenvolvido como demonstração prática de conhecimentos em:

**Dados + BI + SQL + Python + Automação + APIs + Inteligência Artificial.**

O objetivo é demonstrar a capacidade de transformar dados operacionais em informações úteis para apoiar decisões e identificar oportunidades de melhoria.

---

## ⚠️ Dados

Todos os dados utilizados neste projeto são fictícios e não representam informações reais de empresas, clientes ou veículos.

---

## 👩‍💻 Desenvolvido por

**Larissa Mendes Brito**

Projeto desenvolvido para demonstração de conhecimentos em:

**Data Analytics | Business Intelligence | Python | SQL | Power BI | Inteligência Artificial | Automação**
