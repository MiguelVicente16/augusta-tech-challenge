# Sistema de Incentivos Públicos Portugal 🇵🇹

> Sistema inteligente que identifica as 5 melhores empresas para cada incentivo público português e disponibiliza um chatbot RAG para consultas.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19+-61DAFB.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6+-blue.svg)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)](https://www.postgresql.org/)

---

## 📋 Índice

- [Quick Start](#-quick-start)
- [Funcionalidades](#-funcionalidades)
- [Arquitetura](#-arquitetura)
- [Setup & Instalação](#-setup--instalação)
- [Como Usar](#-como-usar)
- [API Endpoints](#-api-endpoints)
- [Performance & Custos](#-performance--custos)
- [Deploy em Produção](#-deploy-em-produção)
- [Challenge Compliance](#-challenge-compliance)

---

## 🚀 Quick Start

**Requisito**: PostgreSQL rodando localmente (ou acessível via `DATABASE_URL`)

```bash
# Terminal 1 - Backend
cd backend && source venv/bin/activate && ./run.sh

# Terminal 2 - Frontend
cd frontend && npm run dev
```

Acesse: **http://localhost:5173**

---

## ✨ Funcionalidades

### 🤖 Chatbot Inteligente
- Interface conversacional com streaming em tempo real
- RAG (Retrieval-Augmented Generation) sobre incentivos e empresas
- Ferramentas especializadas (semantic search, exact queries, matching)
- Resposta em <20s (primeiro chunk)

### 🎯 Matching Engine
- Identifica top 5 empresas para cada incentivo
- Scoring multi-critério baseado em Portugal 2030:
  - **Adequação à Estratégia** (40%): alinhamento setorial
  - **Qualidade** (35%): inovação, complexidade
  - **Capacidade de Execução** (25%): recursos, experiência
- Custo <$0.30 por incentivo
- Exportação de resultados para CSV

### 📊 Interface Web Moderna
- **Incentivos**: listagem, busca, detalhes completos
- **Empresas**: visualização de CAE, setor, website
- **Correspondências**: ranking visual com scores detalhados
- Design minimalista (shadcn/ui + Tailwind CSS v4)

---

## 🏗️ Arquitetura

```
augusta_tech/
├── backend/                    # FastAPI Backend
│   ├── src/
│   │   ├── api/               # API routers & endpoints
│   │   │   ├── main.py        # FastAPI app
│   │   │   └── routers/       # Modular endpoints
│   │   │       ├── chatbot.py        # Chatbot com streaming
│   │   │       ├── matching.py       # Matching engine
│   │   │       ├── data.py           # CRUD operations
│   │   │       └── csv_loader.py     # CSV import
│   │   ├── database/          # Database layer
│   │   │   ├── connection.py  # Connection pooling
│   │   │   ├── schema.py      # SQL schemas
│   │   │   ├── service.py     # Database service
│   │   │   └── sql/           # Query builders
│   │   ├── agents/            # Pydantic AI agents
│   │   │   ├── chatbot_agent.py      # Main chatbot
│   │   │   └── chatbot_tools.py      # Tool definitions
│   │   ├── ai/                # AI integrations
│   │   │   ├── openai_client.py      # OpenAI wrapper
│   │   │   └── prompts.py            # Centralized prompts
│   │   ├── models/            # Pydantic models
│   │   └── config.py          # Settings management
│   ├── data/
│   │   ├── incentives.csv     # 539 incentivos
│   │   └── companies.csv      # 195k empresas
│   └── requirements.txt
│
└── frontend/                   # React + TypeScript
    ├── src/
    │   ├── pages/             # Main pages
    │   │   ├── ChatbotPage.tsx       # Chatbot interface
    │   │   ├── IncentivesPage.tsx    # Incentivos list
    │   │   ├── CompaniesPage.tsx     # Empresas list
    │   │   └── MatchesPage.tsx       # Correspondências
    │   ├── components/        # Reusable UI components
    │   │   └── ui/            # shadcn/ui components
    │   ├── api/               # API client
    │   └── types/             # TypeScript definitions
    └── package.json
```

### Tech Stack

**Backend:**
- **FastAPI** (Python 3.10+): REST API with async support
- **PostgreSQL 14+**: Relational database
- **Pydantic AI**: Agentic chatbot framework
- **OpenAI GPT-4o-mini**: Cost-effective LLM
- **asyncpg**: High-performance PostgreSQL driver
- **Logfire**: Observability & tracing

**Frontend:**
- **React 19**: UI framework
- **TypeScript 5.6+**: Type safety
- **Vite**: Fast build tool
- **Tailwind CSS v4**: Styling
- **shadcn/ui**: Component library
- **React Router**: Navigation
- **Lucide Icons**: Icon set

---

## 🔧 Setup & Instalação

### Pré-requisitos

```bash
# Verificar versões
python --version   # 3.10+
node --version     # 20+
psql --version     # 14+
```

### 1. Setup do Backend

```bash
cd backend

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou .\venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt

# Criar database
createdb incentivos

# Configurar environment
cp .env.example .env
# Editar .env com suas credenciais
```

**Backend `.env`:**
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/incentivos
DB_HOST=localhost
DB_PORT=5432
DB_NAME=incentivos
DB_USER=your_user
DB_PASSWORD=your_password

# OpenAI
OPENAI_API_KEY=sk-proj-...  # Obter em https://platform.openai.com
ENABLE_AI_GENERATION=false
OPENAI_MODEL=gpt-4o-mini
MAX_COST_PER_INCENTIVE=0.30

# API
API_HOST=0.0.0.0
API_PORT=8000
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### 2. Setup do Frontend

```bash
cd frontend

# Instalar dependências
npm install

# Configurar environment (opcional)
cp .env.example .env
```

**Frontend `.env`:**
```bash
VITE_API_BASE_URL=http://localhost:8000
```

---

## 🎮 Como Usar

### Iniciar Serviços

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
./run.sh

# Ou manualmente:
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Backend disponível em:
- **API**: http://localhost:8000
- **Docs interativa**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Frontend disponível em: **http://localhost:5173**

---

### Carregar Dados (Primeira Vez)

```bash
# 1. Carregar empresas (~195k rows, ~30s)
curl -X POST http://localhost:8000/api/v1/load-csv \
  -H "Content-Type: application/json" \
  -d '{"file_name": "companies.csv", "csv_type": "companies"}'

# 2. Carregar incentivos sem AI (~539 rows, ~2s)
curl -X POST http://localhost:8000/api/v1/load-csv \
  -H "Content-Type: application/json" \
  -d '{"file_name": "incentives.csv", "csv_type": "incentives", "enable_ai_generation": false}'

# OU: Carregar incentivos COM structured descriptions (~5-10min, custo ~$1-2)
curl -X POST http://localhost:8000/api/v1/load-csv \
  -H "Content-Type: application/json" \
  -d '{"file_name": "incentives.csv", "csv_type": "incentives", "enable_ai_generation": true}'
```

**Ou use a interface web:**
1. Acesse http://localhost:5173
2. Navegue para qualquer página (Incentivos/Empresas/Matches)
3. Os dados serão carregados automaticamente via API

---

### Gerar Matches

**Via Frontend (Recomendado):**
1. Acesse http://localhost:5173/matches
2. Clique em **"Processar Matches"** para processar apenas incentivos sem matches
3. Ou clique em **"Regenerar Tudo"** para recalcular todos

**Via API:**
```bash
# Matching batch (apenas incentivos sem matches)
curl -X POST http://localhost:8000/api/v1/matching/batch-stream \
  -H "Content-Type: application/json" \
  -d '{"force_refresh": false, "max_total_cost": 150.0}'

# Matching para um incentivo específico
curl -X POST http://localhost:8000/api/v1/matching/run \
  -H "Content-Type: application/json" \
  -d '{"incentive_id": 1, "max_cost": 0.30}'
```

**Exportar matches para CSV:**
```bash
curl -X GET http://localhost:8000/api/v1/matching/export > matches.csv

# Ou use o botão "Exportar CSV" na página de Matches
```

---

## 📡 API Endpoints

### Data Access
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/v1/incentives` | Listar incentivos (paginado, com busca) |
| `GET` | `/api/v1/incentives/{id}` | Obter incentivo por ID |
| `GET` | `/api/v1/incentives/count` | Total de incentivos |
| `GET` | `/api/v1/companies` | Listar empresas (paginado, com busca) |
| `GET` | `/api/v1/companies/{id}` | Obter empresa por ID |
| `GET` | `/api/v1/matches` | Listar matches (filtros opcionais) |
| `GET` | `/api/v1/matches/incentive/{id}/top` | Top 5 matches para incentivo |

### Matching Engine
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/api/v1/matching/run` | Executar matching para 1 incentivo |
| `POST` | `/api/v1/matching/batch` | Matching batch (todos ou novos) |
| `POST` | `/api/v1/matching/batch-stream` | Matching com streaming (SSE) |
| `GET` | `/api/v1/matching/export` | Exportar matches para CSV |

### Chatbot
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/api/v1/chatbot/chat` | Chat com streaming (SSE) |

### CSV Loading
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/api/v1/load-csv` | Carregar CSV individual |
| `POST` | `/api/v1/load-all-csvs` | Carregar todos os CSVs |
| `DELETE` | `/api/v1/clear-data` | Limpar dados (destructive!) |

**Documentação interativa completa**: http://localhost:8000/docs

---

## 💰 Performance & Custos

### Targets do Challenge ✅

| Requisito | Target | Implementado | Status |
|-----------|--------|--------------|--------|
| Matching cost | <$0.30/incentivo | ~$0.20-0.28 | ✅ |
| Chatbot cost | <$15/1k msgs | ~$6-10/1k msgs | ✅ |
| First chunk response | <20s | ~2-8s | ✅ |

### Custos Detalhados

**Matching (por incentivo):**
- Modelo: GPT-4o-mini
- Tokens: ~15k-20k (prompt + completion)
- Custo: **$0.20-0.28** por incentivo
- Total (539 incentivos): **~$110-150**

**Chatbot (por mensagem):**
- Modelo: GPT-4o-mini
- Tokens médios: ~3k-5k
- Custo: **$0.006-0.010** por mensagem
- 1000 mensagens: **~$6-10** (bem abaixo do target de $15)

**Structured Descriptions (one-time):**
- Modelo: GPT-4o-mini
- Custo total: **~$1-2** (539 incentivos)
- Opcional (melhora qualidade do matching)

---

## 🚀 Deploy em Produção

### Opção 1: Supabase + Vercel (Recomendado - Mais Rápido)

**Tempo estimado**: 2-3 horas
**Custo**: $0-25/mês (MVP)

#### 1. Database (Supabase)

**Setup:**
1. Criar projeto em https://supabase.com
2. Obter connection string: `Settings` → `Database` → `Connection string`
3. Executar schema:
   ```bash
   psql "postgresql://postgres:[password]@[host]:5432/postgres" \
     -f backend/src/database/schema.sql
   ```
4. Habilitar extensão pgvector:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

**Vantagens:**
- ✅ PostgreSQL gerenciado
- ✅ pgvector built-in
- ✅ Free tier: 500MB DB, 2GB bandwidth
- ✅ Backups automáticos
- ✅ Connection pooling

#### 2. Backend (Vercel Serverless)

**Criar `vercel.json` na raiz:**
```json
{
  "version": 2,
  "builds": [
    {
      "src": "backend/src/api/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "backend/src/api/main.py"
    }
  ]
}
```

**Deploy:**
```bash
# Instalar Vercel CLI
npm i -g vercel

# Deploy
vercel --prod

# Configurar environment variables no dashboard:
# - DATABASE_URL (Supabase connection string)
# - OPENAI_API_KEY
# - ENABLE_AI_GENERATION=true
```

**⚠️ Limitação**: Timeout de 10s (pode afetar batch matching). Use Railway para workloads longos.

#### 3. Frontend (Vercel)

```bash
cd frontend
vercel --prod

# Environment variable:
# - VITE_API_BASE_URL=https://your-backend.vercel.app
```

---

### Opção 2: Railway (Melhor para Long-Running Jobs)

**Tempo estimado**: 1-2 horas
**Custo**: $5-30/mês

**Vantagens:**
- ✅ Sem timeout limits
- ✅ PostgreSQL + FastAPI no mesmo lugar
- ✅ $5/mês free credit
- ✅ Melhor para batch matching

**Setup:**
1. Conectar GitHub repo em https://railway.app
2. Adicionar PostgreSQL service
3. Adicionar Web service (FastAPI)
4. Deploy frontend separadamente no Vercel/Netlify

---

### Opção 3: Render (Free Tier)

**Tempo estimado**: 2 horas
**Custo**: $0 (free tier com limitações)

**Vantagens:**
- ✅ Completamente grátis
- ✅ PostgreSQL incluído (90 dias)
- ✅ Sem cartão de crédito

**Desvantagens:**
- ⚠️ Services "spin down" após 15min inatividade (cold starts)
- ⚠️ Free PostgreSQL expira após 90 dias

---

## ✅ Production Readiness Checklist

### 🔴 Crítico (Deve Implementar)

- [ ] **Adicionar CORS**: Configurar origens permitidas no FastAPI
  ```python
  # backend/src/api/main.py
  from fastapi.middleware.cors import CORSMiddleware

  app.add_middleware(
      CORSMiddleware,
      allow_origins=["https://your-frontend.vercel.app"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```

- [ ] **Rate Limiting**: Prevenir abuso de API
  ```python
  from slowapi import Limiter
  from slowapi.util import get_remote_address

  limiter = Limiter(key_func=get_remote_address)
  app.state.limiter = limiter
  ```

- [ ] **Environment Validation**: Validar vars obrigatórias no startup
- [ ] **Error Logging**: Integrar Sentry ou similar
- [ ] **Database Migrations**: Script automatizado para schema updates
- [ ] **Health Checks**: Endpoint `/health` detalhado (DB, OpenAI)

### 🟡 Alta Prioridade

- [ ] **Connection Pooling**: Otimizar para serverless (Supabase Pooler)
- [ ] **Caching**: Redis para queries frequentes
- [ ] **Monitoring**: Dashboard básico (Logfire/Datadog)
- [ ] **Cost Alerts**: Monitoramento de uso OpenAI
- [ ] **API Authentication**: JWT para endpoints sensíveis

### 🟢 Nice to Have

- [ ] **CSV Upload**: Endpoint para upload via frontend
- [ ] **Webhooks**: Notificações para batch matching
- [ ] **Admin Dashboard**: Interface para gerenciar dados
- [ ] **E2E Tests**: Smoke tests para CI/CD

---

## 📊 Challenge Compliance

### ✅ Módulo 1: Fontes de Dados
- **Empresas**: `backend/data/companies.csv` (~195k rows)
- **Incentivos**: `backend/data/incentives.csv` (~539 rows)

### ✅ Módulo 2: Base de Dados PostgreSQL

| Campo Requerido | Implementado | Localização |
|-----------------|--------------|-------------|
| `incentive_id` | ✅ `id` (SERIAL PRIMARY KEY) | `backend/src/database/schema.py:14` |
| `title` | ✅ `title` (TEXT NOT NULL) | `backend/src/database/schema.py:17` |
| `description` | ✅ `description` (TEXT) | `backend/src/database/schema.py:18` |
| `ai_description` | ✅ `ai_description_structured` (JSONB) | `backend/src/database/schema.py:20` |
| `document_urls` | ✅ `document_urls` (JSONB) | `backend/src/database/schema.py:22` |
| `publication_date` | ✅ `date_publication` (DATE) | `backend/src/database/schema.py:23` |
| `start_date` | ✅ `date_start` (DATE) | `backend/src/database/schema.py:24` |
| `end_date` | ✅ `date_end` (DATE) | `backend/src/database/schema.py:25` |
| `total_budget` | ✅ `total_budget` (DECIMAL) | `backend/src/database/schema.py:26` |
| `source_link` | ✅ `source_link` (TEXT) | `backend/src/database/schema.py:27` |

**Extras implementados:**
- Full-text search indices (português)
- `matches` table com foreign keys
- `companies` table com CAE classification

### ✅ Módulo 3: Correspondência com Empresas

**Implementação**: `backend/src/api/routers/matching.py`

- **Algoritmo**: Multi-critério scoring (Portugal 2030):
  - Adequação à Estratégia (40%)
  - Qualidade (35%)
  - Capacidade de Execução (25%)
- **Output**: Top 5 empresas por incentivo
- **Cost**: <$0.30 por incentivo ✅
- **Export**: Endpoint `/matching/export` → CSV

### ✅ Módulo 4: Chatbot de Incentivos

**Implementação**: `backend/src/agents/chatbot_agent.py`

- **Framework**: Pydantic AI com tool calling
- **Features**:
  - Query incentivos, empresas, matches
  - Semantic search (pgvector)
  - Streaming SSE (<20s first chunk) ✅
  - Custo <$15/1k msgs ✅
- **Interface**: `frontend/src/pages/ChatbotPage.tsx`

---

## 📝 Database Schema

```sql
-- Incentivos (539 registros)
CREATE TABLE incentives (
    id SERIAL PRIMARY KEY,
    incentive_project_id VARCHAR(255),
    project_id VARCHAR(255),
    title TEXT NOT NULL,
    description TEXT,
    ai_description TEXT,
    ai_description_structured JSONB,  -- {objective, sectors, regions, ...}
    eligibility_criteria JSONB,
    document_urls JSONB,
    date_publication DATE,
    date_start DATE,
    date_end DATE,
    total_budget DECIMAL(15,2),
    source_link TEXT,
    status VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Empresas (~195k registros)
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    company_name TEXT NOT NULL,
    cae_primary_label TEXT,
    trade_description_native TEXT,
    website TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Matches (Top 5 por incentivo)
CREATE TABLE matches (
    id SERIAL PRIMARY KEY,
    incentive_id INTEGER REFERENCES incentives(id) ON DELETE CASCADE,
    company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    score DECIMAL(5,4) CHECK (score >= 0 AND score <= 5),
    rank_position INTEGER CHECK (rank_position >= 1 AND rank_position <= 5),
    reasoning JSONB,  -- {strategic_fit, quality, execution_capacity, rationale}
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(incentive_id, company_id)
);
```

**Índices de Performance:**
- Full-text search (português) em `title`, `description`
- GIN indices em JSONB fields
- Foreign key indices

---

## 🛠️ Scripts Úteis

```bash
# Backend - Formatar código
cd backend
black src/
isort src/

# Frontend - Build & Preview
cd frontend
npm run build
npm run preview

# Database - Backup
pg_dump incentivos > backup.sql

# Database - Restore
psql incentivos < backup.sql

# Logs - Ver logs do backend
tail -f backend/logs/app.log

# Testes
cd backend && pytest
cd frontend && npm test
```

---

## 🤝 Arquitetura de Decisões

### Por que Pydantic AI?
- Tool calling nativo (vs LangChain agents)
- Structured outputs com type safety
- Observability built-in (Logfire)
- Menor overhead que LangChain

### Por que GPT-4o-mini?
- Cost-effective ($0.15/1M input, $0.60/1M output)
- Performance suficiente para matching
- 128k context window
- <$0.30/incentivo garantido

### Por que FastAPI?
- Async/await nativo
- Automatic OpenAPI docs
- Type safety com Pydantic
- Excelente para streaming (SSE)

### Por que PostgreSQL?
- JSONB para structured data
- Full-text search (português)
- pgvector para embeddings
- ACID compliance

---
