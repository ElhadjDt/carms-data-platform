"""
Smoke tests for all 14 API endpoints (13 relational + /health).
Uses an in-memory SQLite database seeded via conftest.py — no live server required.
The QA endpoint is tested with a mock to avoid requiring a real FAISS index or OpenAI key.
"""
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Disciplines
# ---------------------------------------------------------------------------

def test_list_disciplines(client):
    r = client.get("/disciplines/")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    assert data[0]["discipline_name"] == "Family Medicine"


def test_get_discipline(client):
    r = client.get("/disciplines/1")
    assert r.status_code == 200
    assert r.json()["discipline_id"] == 1


def test_get_discipline_not_found(client):
    r = client.get("/disciplines/9999")
    assert r.status_code == 404


def test_get_programs_by_discipline(client):
    r = client.get("/disciplines/1/programs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---------------------------------------------------------------------------
# Programs
# ---------------------------------------------------------------------------

def test_list_programs(client):
    r = client.get("/programs/")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    assert data[0]["program_name"] == "McGill Family Medicine"


def test_list_programs_by_stream(client):
    r = client.get("/programs/10")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---------------------------------------------------------------------------
# Schools
# ---------------------------------------------------------------------------

def test_list_schools(client):
    r = client.get("/schools/")
    assert r.status_code == 200
    assert r.json()[0]["school_name"] == "McGill University"


def test_get_school(client):
    r = client.get("/schools/100")
    assert r.status_code == 200
    assert r.json()["school_id"] == 100


def test_get_school_not_found(client):
    r = client.get("/schools/9999")
    assert r.status_code == 404


def test_get_school_programs(client):
    r = client.get("/schools/100/programs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---------------------------------------------------------------------------
# Sites
# ---------------------------------------------------------------------------

def test_list_sites(client):
    r = client.get("/sites/")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_get_site(client):
    r = client.get("/sites/1")
    assert r.status_code == 200


def test_get_site_not_found(client):
    r = client.get("/sites/9999")
    assert r.status_code == 404


def test_get_site_programs(client):
    r = client.get("/sites/1/programs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---------------------------------------------------------------------------
# Streams
# ---------------------------------------------------------------------------

def test_list_streams(client):
    r = client.get("/streams/")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    assert data[0]["program_stream"] == "CMG"


# ---------------------------------------------------------------------------
# QA endpoint
# ---------------------------------------------------------------------------

def test_qa_endpoint(client):
    with patch("src.api.routers.qa.ask", return_value="Family Medicine focuses on primary care."):
        r = client.post("/qa/", json={"question": "What is family medicine?"})
    assert r.status_code == 200
    assert r.json()["answer"] == "Family Medicine focuses on primary care."


def test_qa_empty_question(client):
    r = client.post("/qa/", json={"question": ""})
    assert r.status_code == 422


def test_qa_question_too_long(client):
    r = client.post("/qa/", json={"question": "x" * 501})
    assert r.status_code == 422
