"""
Shared test fixtures: in-memory SQLite database seeded with minimal test data.
The get_db dependency is overridden so no real PostgreSQL instance is needed.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from unittest.mock import MagicMock, patch

from src.api.main import app
from src.api.deps import get_db
from src.db.models import Discipline, School, Stream, Site, Program

TEST_DATABASE_URL = "sqlite://"


@pytest.fixture(scope="session")
def test_engine():
    # StaticPool keeps a single connection alive across threads so the
    # in-memory SQLite database is shared between the seeding code (main
    # thread) and FastAPI's sync route handlers (run in a worker thread).
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="session")
def seed_db(test_engine):
    """Seed the in-memory database with one record per table."""
    Session = sessionmaker(bind=test_engine)
    session = Session()

    discipline = Discipline(discipline_id=1, discipline_name="Family Medicine")
    school = School(school_id=100, school_name="McGill University")
    stream = Stream(
        program_stream_id=10,
        program_stream="CMG",
        program_stream_name="CMG Stream for CMG",
    )
    site = Site(site_name="Montreal General Hospital")

    session.add_all([discipline, school, stream, site])
    session.flush()

    program = Program(
        discipline_id=1,
        school_id=100,
        program_stream_id=10,
        site_id=site.site_id,
        program_name="McGill Family Medicine",
        program_url="https://fmed.mcgill.ca",
    )
    session.add(program)
    session.commit()
    session.close()


@pytest.fixture(scope="session")
def client(test_engine, seed_db):
    """TestClient with get_db overridden to use the in-memory SQLite database."""
    TestSession = sessionmaker(bind=test_engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with patch("src.qa.qa_chain.load_vectorstore", return_value=MagicMock()), \
         patch("src.qa.qa_chain.build_qa_chain", return_value=MagicMock()):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()
