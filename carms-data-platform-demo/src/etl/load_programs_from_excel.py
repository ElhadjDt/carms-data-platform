import logging

import pandas as pd
from sqlmodel import Session, select
from src.db.session import engine
from src.db.models import Program, School, Stream, Site, Discipline

logger = logging.getLogger(__name__)


def load_programs(filepath: str):
    """
    Load schools, streams, sites, and programs from a single Excel file.
    Uses Excel column names directly to avoid mapping errors.
    Ensures foreign keys exist, creates missing dimension records,
    and avoids duplicate program entries.
    """

    df = pd.read_excel(filepath)

    required_cols = {
        "discipline_id",
        "school_id",
        "school_name",
        "program_stream_id",
        "program_stream",
        "program_stream_name",
        "program_site",
        "program_name",
        "program_url",
    }

    if not required_cols.issubset(df.columns):
        raise ValueError(f"Missing required columns: {required_cols}")

    with Session(engine) as session:
        for _, row in df.iterrows():

            # -----------------------------
            # Extract Excel columns directly
            # -----------------------------
            discipline_id = int(row["discipline_id"])
            school_id = int(row["school_id"])
            school_name = str(row["school_name"]).strip()

            program_stream_id = int(row["program_stream_id"])
            program_stream = str(row["program_stream"]).strip()
            program_stream_name = str(row["program_stream_name"]).strip()

            program_site = str(row["program_site"]).strip()

            program_name = str(row["program_name"]).strip()
            program_url = str(row["program_url"]).strip()

            # -----------------------------
            # Validate discipline (must exist)
            # -----------------------------
            if not session.get(Discipline, discipline_id):
                logger.warning("Skipping program: discipline %d not found.", discipline_id)
                continue

            # -----------------------------
            # SCHOOL: get or create
            # -----------------------------
            school = session.get(School, school_id)
            if not school:
                school = School(
                    school_id=school_id,
                    school_name=school_name
                )
                session.add(school)
                session.commit()
                session.refresh(school)

            # -----------------------------
            # STREAM: get or create
            # -----------------------------
            stream = session.get(Stream, program_stream_id)
            if not stream:
                stream = Stream(
                    program_stream_id=program_stream_id,
                    program_stream=program_stream,
                    program_stream_name=program_stream_name
                )
                session.add(stream)
                session.commit()
                session.refresh(stream)

            # -----------------------------
            # SITE: get or create
            # -----------------------------
            site = session.exec(
                select(Site).where(Site.site_name == program_site)
            ).first()

            if not site:
                site = Site(site_name=program_site)
                session.add(site)
                session.commit()
                session.refresh(site)

            # -----------------------------
            # PROGRAM: check duplicates
            # -----------------------------
            existing_program = session.exec(
                select(Program).where(
                    Program.program_name == program_name,
                    Program.school_id == school_id,
                    Program.discipline_id == discipline_id,
                    Program.program_stream_id == program_stream_id,
                    Program.site_id == site.site_id,
                )
            ).first()

            if existing_program:
                logger.debug("Program already exists, skipping: %s", program_name)
                continue

            # -----------------------------
            # Create Program
            # -----------------------------
            program = Program(
                discipline_id=discipline_id,
                school_id=school_id,
                program_stream_id=program_stream_id,
                site_id=site.site_id,
                program_name=program_name,
                program_url=program_url,
            )

            session.add(program)

        # Final commit
        session.commit()

    logger.info("1503_program_master.xlsx successfully loaded into the database.")


if __name__ == "__main__":
    from src.config import settings
    load_programs(settings.PROGRAM_MASTER_EXCEL)
