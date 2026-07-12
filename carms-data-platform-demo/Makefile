# CARMS Data Platform — one-command setup and run targets.
# Run from carms-data-platform-demo directory: make help | make build | make api | make clean

.ONESHELL:
.SHELL := /bin/bash

.PHONY: help venv install db init-db etl embeddings api dagster dashboard setup build clean

help:
	@echo ""
	@echo "CARMS Data Platform — Available Commands"
	@echo ""
	@echo "  make venv        Create Python virtual environment"
	@echo "  make install     Install dependencies into venv"
	@echo "  make db          Start PostgreSQL (Docker)"
	@echo "  make init-db     Create database schema"
	@echo "  make etl         Run ETL pipeline"
	@echo "  make embeddings  Build FAISS index"
	@echo "  make api         Run FastAPI backend"
	@echo "  make dagster     Run Dagster UI (orchestration)"
	@echo "  make dashboard   Run Streamlit visualization dashboard"
	@echo "  make setup       DB + init-db + etl + embeddings"
	@echo "  make build       venv + install + setup (full project build)"
	@echo "  make clean       Remove venv, containers, volumes, images, and generated data"
	@echo ""

# Create virtual environment
venv:
	python3 -m venv .venv

# Install dependencies
install:
	. .venv/bin/activate
	pip install --upgrade pip
	pip install -r requirements.txt

# Start PostgreSQL
db:
	docker compose up -d db
	echo "DB running at localhost:5432"

# Initialize database schema
init-db:
	. .venv/bin/activate
	python -m src.db.init_db

# Run ETL pipeline
etl:
	. .venv/bin/activate
	python -m src.etl.extract_zip
	python -m src.etl.load_disciplines_from_excel
	python -m src.etl.load_programs_from_excel
	python -m src.etl.load_program_documents_from_csv

# Build FAISS embeddings
embeddings:
	. .venv/bin/activate
	python -m src.qa.embeddings

# Run FastAPI backend
api:
	. .venv/bin/activate
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Run Dagster UI for pipeline orchestration
dagster:
	. .venv/bin/activate
	dg dev -m src.etl.dagster_defs

# Run Streamlit dashboard (calls API; set API_URL if API runs elsewhere)
dashboard:
	. .venv/bin/activate
	streamlit run dashboard/app.py --server.port 8501

# Setup: DB + schema + ETL + embeddings
setup: db
	echo "Waiting for PostgreSQL to be ready..."
	sleep 5
	$(MAKE) init-db
	$(MAKE) etl
	$(MAKE) embeddings
	echo "Setup complete."

# Full build: venv + install + setup
build: venv install setup
	echo "Full build complete. Run 'make api' to start the backend."

# Clean everything: containers, volumes, images (incl. Ollama), venv, generated data
clean:
	docker compose --profile ollama down -v --rmi all --remove-orphans
	rm -rf .venv
	# extracted/embeddings are written by containers running as root, so a plain
	# host-side rm can't remove them — delete via a throwaway container instead.
	docker run --rm -v "$$(pwd)/../data:/data" alpine rm -rf /data/extracted /data/embeddings
	echo "Clean complete."