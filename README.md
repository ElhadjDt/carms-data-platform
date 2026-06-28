# CaRMS Data Platform

A containerized data platform built on public CaRMS residency program data. Demonstrates end-to-end data engineering: automated ETL pipelines, a normalized PostgreSQL database, a REST API, a RAG Q&A system, and an analytics dashboard — all orchestrated with Docker Compose.

---

## Quick Start

```bash
git clone https://github.com/ElhadjDt/carms-data-platform.git
cd carms-data-platform/carms-data-platform-demo

cp .env.example .env          # add your OPENAI_API_KEY

docker compose build
docker compose up -d db
docker compose run --rm init-db
docker compose run --rm etl
docker compose run --rm embeddings
docker compose up -d api dashboard
```

| Service | URL |
|---------|-----|
| API (Swagger UI) | http://localhost:8000/docs |
| Streamlit dashboard | http://localhost:8501 |
| Dagster (optional) | http://localhost:3000 |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Database | PostgreSQL 16 |
| ORM | SQLModel / SQLAlchemy |
| API | FastAPI |
| Dashboard | Streamlit + Plotly |
| ETL orchestration | Dagster |
| RAG pipeline | LangChain + FAISS + OpenAI or Ollama |
| Infrastructure | Docker & Docker Compose |

---

## Table of Contents

1. [Setup](#setup)
2. [Database Design](#database-design)
3. [RAG Q&A System](#rag-qa-system)
4. [API Reference](#api-reference)
5. [Environment Variables](#environment-variables)
6. [Troubleshooting](#troubleshooting)

---

## Setup

### Prerequisites

- Docker and Docker Compose
- An OpenAI API key **or** [Ollama](https://ollama.com) running locally (see [Ollama mode](#ollama-offline-mode))
- 4 GB RAM available to Docker (8 GB recommended — see [memory requirements](#troubleshooting))

### Step-by-step

**1. Configure environment**

```bash
cp .env.example .env
# Edit .env: set OPENAI_API_KEY (or switch to Ollama — see below)
```

**2. Build the image**

```bash
docker compose build
```

**3. Initialize the database**

```bash
docker compose up -d db
docker compose run --rm init-db
```

**4. Run the ETL pipeline**

Extracts ZIP archives, loads disciplines and programs, and loads program descriptions into the database.

```bash
docker compose run --rm etl
```

**5. Generate embeddings**

Chunks program descriptions, embeds them with the configured provider, and builds the FAISS index.

```bash
docker compose run --rm embeddings
# Index saved to: data/embeddings/faiss_index
```

**6. Start the application**

```bash
docker compose up -d api dashboard

# Optional: Dagster orchestration UI
docker compose up -d dagster
```

### Ollama (offline) mode

Run the full platform without an OpenAI key using local models via [Ollama](https://ollama.com).

```bash
# 1. Start the Ollama service and pull the required models
docker compose --profile ollama up -d ollama
docker exec carms_ollama ollama pull llama3.2
docker exec carms_ollama ollama pull nomic-embed-text

# 2. Switch providers in .env
#    LLM_PROVIDER=ollama
#    EMBEDDING_PROVIDER=ollama

# 3. Build the FAISS index with Ollama embeddings
docker compose run --rm embeddings

# 4. Start the application normally
docker compose up -d api dashboard
```

> **Note:** If you previously built the FAISS index with OpenAI, you must re-run `embeddings` after switching — the vector dimensions are incompatible (1536 vs 768).

### Service management

```bash
# Check running containers
docker compose ps

# Stream logs for a service
docker compose logs -f api

# Stop all services
docker compose down

# Stop and remove the PostgreSQL volume
docker compose down -v
```

---

## Database Design

### Problem

The raw CaRMS data ships as two Excel files: `1503_discipline.xlsx` and `1503_program_master.xlsx`. The program master file mixes discipline, school, stream, site, and program attributes into a single flat table — storing everything together violates normalization rules and creates update, insertion, and deletion anomalies.

### Normalized Schema (3NF)

The program master file is decomposed into four relational tables, plus a fifth table for program descriptions loaded from CSV:

**Table: discipline**

| Column | Type |
|--------|------|
| discipline_id | PK |
| discipline_name | Text |

**Table: school**

| Column | Type |
|--------|------|
| school_id | PK |
| school_name | Text |

**Table: stream**

| Column | Type |
|--------|------|
| program_stream_id | PK |
| program_stream | Text |
| program_stream_name | Text |

**Table: site**

| Column | Type |
|--------|------|
| site_id | PK (auto-increment) |
| site_name | Text |

**Table: program**

| Column | Type |
|--------|------|
| program_id | PK (auto-increment) |
| discipline_id | FK → discipline |
| school_id | FK → school |
| program_stream_id | FK → stream |
| site_id | FK → site |
| program_name | Text |
| program_url | Text |

**Table: program_document**

| Column | Type |
|--------|------|
| id | PK (auto-increment) |
| program_id | FK → program |
| section_name | Text |
| content | Text |
| source | Text |

![Entity-relationship diagram](docs/imgs/db_relations.png)

### Population

The ETL pipeline loads both Excel files row-by-row using SQLModel, resolving dimension records (school, stream, site) with get-or-create logic before inserting each program. Program descriptions are loaded from `1503_program_descriptions_x_section.csv` and normalized wide-to-long into `program_document`.

---

## RAG Q&A System

The platform includes a Retrieval-Augmented Generation pipeline that answers natural language questions about residency programs.

**Pipeline:**

1. Program descriptions from `program_document` are chunked (500 tokens, 50-token overlap)
2. Each chunk is embedded and stored in a FAISS index
3. At query time, the top-5 most relevant chunks are retrieved
4. An LLM generates an answer grounded in the retrieved context

**Providers** (set via env vars — no code changes needed):

| `EMBEDDING_PROVIDER` | Model | `LLM_PROVIDER` | Model |
|---|---|---|---|
| `openai` (default) | `text-embedding-3-small` | `openai` (default) | `gpt-4o-mini` |
| `ollama` | `nomic-embed-text` | `ollama` | `llama3.2` |

The QA system is exposed as a REST endpoint (`POST /qa`) and through the Streamlit dashboard.

![FAISS index creation](docs/imgs/faiss.png)

---

## API Reference

The FastAPI backend exposes 14 endpoints across two categories.

**Relational data** — `GET /disciplines`, `/programs`, `/schools`, `/sites`, `/streams` (with individual record lookup by ID), and `GET /health`

![Database endpoints](docs/imgs/db_api.png)

**Q&A** — `POST /qa` — accepts a question string (1–500 characters), returns an LLM answer grounded in program descriptions

![Q&A endpoint](docs/imgs/qa_api.png)

![Q&A QR code](docs/imgs/qa_qr.png)

Full endpoint details with example request and response values: [docs/api-endpoints.md](docs/api-endpoints.md)

Interactive documentation available at **http://localhost:8000/docs** once the API is running.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | When `*_PROVIDER=openai` | — | OpenAI API key |
| `POSTGRES_USER` | No | `carms` | PostgreSQL username |
| `POSTGRES_PASSWORD` | No | `carms` | PostgreSQL password |
| `POSTGRES_DB` | No | `carms_db` | PostgreSQL database name |
| `DATABASE_URL` | No | `postgresql+psycopg2://carms:carms@db:5432/carms_db` | Full connection string |
| `LLM_PROVIDER` | No | `openai` | LLM backend: `openai` or `ollama` |
| `EMBEDDING_PROVIDER` | No | `openai` | Embedding backend: `openai` or `ollama` |
| `OLLAMA_HOST` | No | `http://ollama:11434` | Ollama server URL |
| `OLLAMA_LLM_MODEL` | No | `llama3.2` | Ollama model for generation |
| `OLLAMA_EMBEDDING_MODEL` | No | `nomic-embed-text` | Ollama model for embeddings |
| `DATA_DIR` | No | `/data` (inside container) | Path to the data directory |
| `FAISS_PATH` | No | `{DATA_DIR}/embeddings/faiss_index` | Path to the FAISS index |
| `CORS_ORIGINS` | No | `http://localhost:8501` | Comma-separated allowed origins for the API |

All variables can be set in `.env` (gitignored). Docker Compose injects them into each container.

---

## Troubleshooting

**Database won't start**
```bash
docker compose logs db
# Common cause: port 5432 already in use locally
# Fix: stop local PostgreSQL, or change the port mapping in docker-compose.yml
```

**ETL fails with "Missing required columns"**

The raw data files must be present at `data/raw/` before running the ETL. Verify:
```bash
ls data/raw/
# Should include: 1503_discipline.xlsx, 1503_program_master.xlsx, *.zip
```

**Embeddings fail — OpenAI error**

Check that `OPENAI_API_KEY` is set in `.env` and has sufficient quota. The embeddings step calls the OpenAI API and will fail with `AuthenticationError` if the key is missing or invalid.

**Out of memory during setup**

The full stack requires ~3.1 GB RAM at peak (all services starting simultaneously). If Docker OOMs, increase memory in Docker Desktop settings or run setup steps one at a time with pauses between.

**FAISS index not found when starting API**

The embeddings step must complete before the API starts. Run `docker compose run --rm embeddings` and confirm `data/embeddings/faiss_index/` exists before `docker compose up -d api`.

---

## AWS Deployment

A production deployment architecture mapping this platform to managed AWS services (RDS, ECS Fargate, S3, Secrets Manager) is documented in [docs/aws-architecture.md](docs/aws-architecture.md).
