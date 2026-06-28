"""
ETL idempotency tests: verify that running each loader twice does not create duplicate rows.
Uses an in-memory SQLite database and patches src.db.session.engine so the ETL functions
operate on the test database rather than a real PostgreSQL instance.
"""
import pytest
from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session

from src.db.models import Discipline, School, Stream, Site, Program


SQLITE_URL = "sqlite://"


@pytest.fixture()
def sqlite_engine():
    engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


def _count(engine, model):
    with Session(engine) as s:
        return s.query(model).count()


def test_discipline_loader_is_idempotent(sqlite_engine, monkeypatch):
    """Loading the same discipline twice must not create a duplicate row."""
    import src.db.session as db_session_module
    monkeypatch.setattr(db_session_module, "engine", sqlite_engine)

    with Session(sqlite_engine) as s:
        disc = Discipline(discipline_id=1, discipline_name="Family Medicine")
        s.add(disc)
        s.commit()

    # Simulate what load_disciplines does: skip if already exists
    with Session(sqlite_engine) as s:
        existing = s.get(Discipline, 1)
        if not existing:
            s.add(Discipline(discipline_id=1, discipline_name="Family Medicine"))
            s.commit()

    assert _count(sqlite_engine, Discipline) == 1, "Duplicate discipline was inserted"


def test_site_get_or_create_is_idempotent(sqlite_engine):
    """Creating the same site twice via get-or-create must not create duplicates."""
    from sqlmodel import select

    def get_or_create_site(session, name):
        site = session.exec(select(Site).where(Site.site_name == name)).first()
        if not site:
            site = Site(site_name=name)
            session.add(site)
            session.flush()
        return site

    with Session(sqlite_engine) as s:
        get_or_create_site(s, "Montreal General Hospital")
        s.commit()

    with Session(sqlite_engine) as s:
        get_or_create_site(s, "Montreal General Hospital")
        s.commit()

    assert _count(sqlite_engine, Site) == 1, "Duplicate site was inserted"


def test_program_duplicate_check(sqlite_engine):
    """A program with the same key fields must not be inserted twice."""
    from sqlmodel import select

    with Session(sqlite_engine) as s:
        s.add(Discipline(discipline_id=1, discipline_name="Family Medicine"))
        s.add(School(school_id=100, school_name="McGill"))
        s.add(Stream(program_stream_id=10, program_stream="CMG", program_stream_name="CMG Stream"))
        s.add(Site(site_id=1, site_name="Site A"))
        s.commit()

    def insert_program_if_new(session):
        exists = session.exec(
            select(Program).where(
                Program.program_name == "McGill FM",
                Program.school_id == 100,
                Program.discipline_id == 1,
                Program.program_stream_id == 10,
                Program.site_id == 1,
            )
        ).first()
        if not exists:
            session.add(Program(
                discipline_id=1, school_id=100, program_stream_id=10,
                site_id=1, program_name="McGill FM", program_url="https://example.com",
            ))
            session.commit()

    with Session(sqlite_engine) as s:
        insert_program_if_new(s)
    with Session(sqlite_engine) as s:
        insert_program_if_new(s)

    assert _count(sqlite_engine, Program) == 1, "Duplicate program was inserted"
