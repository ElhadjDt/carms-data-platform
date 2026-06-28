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
| RAG pipeline | LangChain + OpenAI + FAISS |
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
- An OpenAI API key
- 4 GB RAM available to Docker (8 GB recommended — see [memory requirements](#troubleshooting))

### Step-by-step

**1. Configure environment**

```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY
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

Chunks program descriptions, generates OpenAI embeddings, and builds the FAISS index.

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

Raw CaRMS data is denormalized across two Excel files. This platform decomposes it into a **3NF relational schema** to eliminate update, insertion, and deletion anomalies.

### Schema

**discipline** — `discipline_id (PK)`, `discipline_name`

**school** — `school_id (PK)`, `school_name`

**stream** — `program_stream_id (PK)`, `program_stream`, `program_stream_name`

**site** — `site_id (PK, auto)`, `site_name`

**program** — `program_id (PK, auto)`, `discipline_id (FK)`, `school_id (FK)`, `program_stream_id (FK)`, `site_id (FK)`, `program_name`, `program_url`

**program_document** — `id (PK, auto)`, `program_id (FK)`, `section_name`, `content`, `source`

![Entity-relationship diagram](docs/imgs/db_relations.png)

### Population

The ETL pipeline loads `1503_discipline.xlsx` and `1503_program_master.xlsx` row-by-row using SQLModel, resolving dimension records (school, stream, site) with get-or-create logic before inserting each program.

---

## RAG Q&A System

The platform includes a Retrieval-Augmented Generation pipeline that answers natural language questions about residency programs.

**Pipeline:**

1. Program descriptions from `program_document` are chunked (500 tokens, 50-token overlap)
2. Each chunk is embedded with `text-embedding-3-small` and stored in a FAISS index
3. At query time, the top-5 most relevant chunks are retrieved
4. `gpt-4o-mini` generates an answer grounded in the retrieved context

The QA system is exposed as a REST endpoint (`POST /qa`) and through the Streamlit dashboard.

![FAISS index creation](docs/imgs/faiss.png)

---

## API Reference

The FastAPI backend exposes 13 endpoints across two categories:

**Relational data** — `GET /disciplines`, `/programs`, `/schools`, `/sites`, `/streams` (with individual record lookup by ID)

**Q&A** — `POST /qa` — accepts a question string, returns an LLM answer grounded in program descriptions

Full interactive documentation is available at **http://localhost:8000/docs** (Swagger UI) once the API is running.

![Database endpoints](docs/imgs/db_api.png)

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key for embeddings and Q&A |
| `DATABASE_URL` | No | `postgresql+psycopg2://carms:carms@localhost:5432/carms_db` | PostgreSQL connection string |
| `DATA_DIR` | No | `../data` (repo root) | Path to the data directory |
| `FAISS_PATH` | No | `{DATA_DIR}/embeddings/faiss_index` | Path to the FAISS index |

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
