import logging

import pandas as pd
from sqlmodel import Session
from src.db.session import engine
from src.db.models import Discipline

logger = logging.getLogger(__name__)


def load_disciplines(filepath: str):
    """
    Load disciplines from an Excel file and insert them into the database.
    Avoids duplicates based on discipline_id.
    """

    df = pd.read_excel(filepath)

    required_cols = {"discipline_id", "discipline"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"Missing required columns: {required_cols}")

    with Session(engine) as session:
        for _, row in df.iterrows():
            discipline_id = int(row["discipline_id"])
            name = str(row["discipline"]).strip()

            # Check if discipline already exists
            existing = session.get(Discipline, discipline_id)
            if existing:
                logger.debug("Discipline already exists, skipping: %s (id=%d)", name, discipline_id)
                continue

            # Create new Discipline object
            discipline = Discipline(
                discipline_id=discipline_id,
                discipline_name=name
            )

            session.add(discipline)

        session.commit()

    logger.info("Disciplines successfully loaded into the database from 1503_discipline.xlsx.")


if __name__ == "__main__":
    from src.config import settings
    load_disciplines(settings.DISCIPLINE_EXCEL)
