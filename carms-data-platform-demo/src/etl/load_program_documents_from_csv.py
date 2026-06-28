import logging

import pandas as pd
from sqlmodel import Session, select
from src.db.models import Program, ProgramDocument
from src.db.session import engine

logger = logging.getLogger(__name__)


SECTION_COLUMNS = [
    "program_contracts",
    "general_instructions",
    "supporting_documentation_information",
    "review_process",
    "interviews",
    "selection_criteria",
    "program_highlights",
    "program_curriculum",
    "training_sites",
    "additional_information",
    "return_of_service",
    "faq",
    "summary_of_changes",
]


def load_program_documents(filepath: str):
    """
    Loads CaRMS program descriptions from CSV, normalizes them
    (wide → long), maps them to Program via program_description_id,
    and inserts them into ProgramDocument.
    """
    logger.info("Loading program descriptions from: %s", filepath)
    df = pd.read_csv(filepath)

    with Session(engine) as session:
        inserted = 0
        skipped = 0

        for _, row in df.iterrows():

            stmt = select(Program).where(
                Program.program_stream_id == row["program_description_id"]
            )
            program = session.exec(stmt).first()

            if not program:
                logger.warning("No Program found for program_description_id=%s", row['program_description_id'])
                skipped += 1
                continue

            for section in SECTION_COLUMNS:
                content = row.get(section)

                if not isinstance(content, str) or content.strip() == "":
                    continue

                doc = ProgramDocument(
                    program_id=program.program_id,
                    section_name=section,
                    content=content.strip(),
                    program_description_id=row["program_description_id"],
                    document_id=row["document_id"],
                    match_iteration_id=row["match_iteration_id"],
                    source=row["source"],
                )

                session.add(doc)
                inserted += 1

        session.commit()

    logger.info("ProgramDocument loading complete. Inserted: %d, Skipped: %d", inserted, skipped)

if __name__ == "__main__":
    from src.config import settings
    load_program_documents(settings.PROGRAM_DESCRIPTIONS_CSV)
