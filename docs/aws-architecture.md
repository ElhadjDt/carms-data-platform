# AWS Deployment Architecture

This document maps the platform's current local Docker Compose setup onto managed AWS services for a production-style deployment — same logical components, cloud infrastructure instead of local containers.

## Table of Contents

1. [Overview](#1-overview)
2. [Current Local Architecture](#2-current-local-architecture)
3. [Target AWS Architecture](#3-target-aws-architecture)
4. [Storage Strategy](#4-storage-strategy)
5. [Deployment Flow](#5-deployment-flow)
6. [Environment Variables](#6-environment-variables)
7. [Security Considerations](#7-security-considerations)
8. [Cost Optimization](#8-cost-optimization)

---

## 1. Overview

The platform consists of:

- **PostgreSQL** — normalized relational database
- **ETL pipelines** — load CaRMS program data into Postgres
- **Embedding pipeline** — builds a FAISS vector index (Ollama locally by default, OpenAI in this AWS target — see [§3](#3-target-aws-architecture))
- **FastAPI backend** — exposes relational and RAG (`/qa`) endpoints
- **Streamlit dashboard** — analytics UI
- **Dagster** — optional ETL/embedding orchestration UI

---

## 2. Current Local Architecture

Runs as a set of Docker Compose services:

| Service | Purpose |
|------|------|
| `db` | PostgreSQL database |
| `init-db` | Creates the relational schema |
| `etl` | Loads CaRMS datasets into PostgreSQL |
| `ollama` | Local LLM/embedding server — default provider, profile-gated |
| `embeddings` | Generates the FAISS vector index |
| `api` | FastAPI backend exposing database + RAG endpoints |
| `dashboard` | Streamlit analytics dashboard |
| `dagster` | Optional ETL/embedding orchestration UI |

### Shared Data Directory

All services share a mounted repository-level directory:

```
data/
├── raw
├── extracted
└── embeddings
```

| Folder | Purpose |
|------|------|
| `raw` | Original CaRMS data files |
| `extracted` | ETL-generated structured files |
| `embeddings` | FAISS vector index |

### Local Architecture Diagram

`ollama` and `dagster` are omitted below for clarity (see the containers table above) — the diagram shows the core data pipeline: schema → data → index → API → dashboard.

```
                    ┌─────────────────────────────┐
                    │      Docker Compose         │
                    └──────────────┬──────────────┘
                                   │
     ┌─────────────────────────────┼─────────────────────────────┐
     │                             │                             │
     ▼                             ▼                             ▼
┌──────────────┐           ┌──────────────┐              ┌──────────────┐
│   init-db    │           │     etl      │              │  embeddings  │
│ create schema│           │ load data    │              │ build FAISS  │
└──────┬───────┘           └──────┬───────┘              └──────┬───────┘
       │                          │                             │
       └──────────────┬───────────┴──────────────┬──────────────┘
                      │                          │
                      ▼                          ▼
               ┌──────────────┐         ┌────────────────┐
               │ PostgreSQL   │         │ data/          │
               │ normalized DB│         │ raw/extracted/ │
               └──────┬───────┘         │ embeddings/    │
                      │                 └────────────────┘
                      ▼
               ┌──────────────┐
               │   FastAPI    │
               │ DB + RAG API │
               └──────┬───────┘
                      ▼
               ┌──────────────┐
               │  Streamlit   │
               │ Dashboard    │
               └──────────────┘
```

---

## 3. Target AWS Architecture

Same logical components, on managed AWS services. **This target assumes OpenAI for LLM/embeddings** — Ollama is a convenience for local/offline development, not part of this production design.

> Self-hosting Ollama on AWS (e.g. an EC2 GPU instance) is a valid alternative if avoiding per-token API costs matters more than operational simplicity, but it adds meaningfully more infrastructure to manage than a fully managed API. This document targets the simpler path.

### AWS Services

| Component | AWS Service | Purpose |
|-----------|-------------|--------|
| Database | Amazon RDS PostgreSQL | Managed relational database |
| API + RAG | ECS Fargate or AWS App Runner | Run the FastAPI container |
| LLM + embeddings | OpenAI API | Generation and embeddings |
| Data storage | Amazon S3 | Store raw data and FAISS artifacts |
| Secrets | AWS Secrets Manager | Store API keys and database credentials |
| ETL orchestration | ECS scheduled tasks / Dagster / Step Functions | Run ETL and embedding generation |
| Dashboard | App Runner / ECS / local | Streamlit analytics interface |

### AWS Architecture Diagram

```
                    ┌─────────────────────────────────────────────────────┐
                    │                     AWS Cloud                       │
                    │                                                     │
Users / Clients ───▶│   ┌──────────────────────────────┐                  │
                    │   │   ECS Fargate / App Runner   │                  │
                    │   │      FastAPI + RAG API       │                  │
                    │   └───────────────┬──────────────┘                  │
                    │                   │                                 │
                    │                   ▼                                 │
                    │         ┌────────────────────┐                      │
                    │         │   Amazon RDS       │                      │
                    │         │   PostgreSQL       │                      │
                    │         └────────────────────┘                      │
                    │                                                     │
                    │                   ▲                                 │
                    │                   │                                 │
                    │   ┌───────────────┴──────────────┐                  │
                    │   │ ETL / Embeddings Jobs        │                  │
                    │   │ ECS Tasks / Dagster /        │                  │
                    │   │ Step Functions               │                  │
                    │   └───────────────┬──────────────┘                  │
                    │                   │                                 │
                    │                   ▼                                 │
                    │         ┌────────────────────┐                      │
                    │         │     Amazon S3      │                      │
                    │         │ raw + extracted +  │                      │
                    │         │ embeddings / FAISS │                      │
                    │         └────────────────────┘                      │
                    │                                                     │
                    │         ┌────────────────────┐                      │
                    │         │ Secrets Manager    │                      │
                    │         │ API keys / DB creds│                      │
                    │         └────────────────────┘                      │
                    └─────────────────────────────────────────────────────┘
```

---

## 4. Storage Strategy

### Relational Database

The normalized relational schema is stored in **Amazon RDS PostgreSQL**.

### Raw and Processed Data

Source files and ETL outputs are stored in **Amazon S3**, including:

- raw Excel and ZIP files
- extracted CSV files
- generated metadata artifacts

### FAISS Vector Index

The FAISS index can be handled in several ways:

1. Bundled inside the API container image
2. Stored in S3 and downloaded at container startup
3. Stored in Amazon EFS and mounted into the container

For lightweight deployments, storing the FAISS index in **S3** is usually sufficient.

---

## 5. Deployment Flow

### Step 1 — Create RDS Database

Provision an **Amazon RDS PostgreSQL** instance and configure:

- database name
- credentials
- VPC and security groups

Run schema initialization:

```
python -m src.db.init_db
```

with `DATABASE_URL` pointing to the RDS instance.

### Step 2 — Build and Push Docker Image

Build the API container image from the project Dockerfile and push it to **Amazon ECR**.

Example:

```
docker build -t carms-api .
docker tag carms-api:latest <aws_account>.dkr.ecr.<region>.amazonaws.com/carms-api
docker push <aws_account>.dkr.ecr.<region>.amazonaws.com/carms-api
```

### Step 3 — Run ETL and Embedding Pipelines

Execute ETL and embedding generation using:

- ECS tasks
- scheduled ECS jobs
- Dagster running on ECS
- Step Functions workflows

Generated data and vector artifacts are stored in **S3**.

### Step 4 — Deploy FastAPI API

Deploy the API container using:

- **AWS App Runner** for simple managed deployments
- **ECS Fargate** for more infrastructure control

Environment variables are injected from **Secrets Manager**.

### Step 5 — Deploy or Connect the Dashboard

The Streamlit dashboard can:

- run locally against the deployed API
- or be deployed as a container on App Runner or ECS

---

## 6. Environment Variables

The AWS deployment uses the same configuration model as local — this is what's actually needed for the OpenAI-mode target described in [§3](#3-target-aws-architecture). See the main [README](../README.md#environment-variables) for the full variable list, including the Ollama-specific ones used only in local/offline mode.

| Variable | Purpose |
|------|------|
| `DATABASE_URL` | PostgreSQL connection string (RDS endpoint) |
| `LLM_PROVIDER` / `EMBEDDING_PROVIDER` | Set to `openai` for this target |
| `OPENAI_API_KEY` | OpenAI API key (from Secrets Manager) |
| `DATA_DIR` | Base data directory |
| `FAISS_PATH` | Path to FAISS vector index |
| `API_URL` | Base URL for the Streamlit dashboard |
| `CORS_ORIGINS` | Allowed origins for the API |

Example:

```
DATABASE_URL=postgresql+psycopg2://user:password@rds-endpoint:5432/carms_db
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=...
DATA_DIR=/data
FAISS_PATH=/data/embeddings/faiss_index
```

---

## 7. Security Considerations

- Place **RDS in private subnets**
- Use **security groups** to restrict database access
- Store secrets in **AWS Secrets Manager**
- Use **IAM roles for ECS tasks**
- Avoid storing credentials in the container image

---

## 8. Cost Optimization

For a demonstration deployment:

- use small **RDS instance types**
- start with **single-AZ** deployment
- run ETL pipelines as **on-demand tasks**
- keep the dashboard optional if API access is sufficient
