"""
Extract CaRMS ZIP archives from raw data directory into extracted directory.
Uses paths from src.config for Docker and local consistency.
"""
import logging
import zipfile
from src.config import settings

logger = logging.getLogger(__name__)


def extract_zip():
    """
    Extract all ZIP files from configured raw dir into extracted dir.
    Creates extracted dir if needed; assumes raw dir exists.
    """
    raw_dir = settings.RAW_DIR
    extracted_dir = settings.EXTRACTED_DIR
    extracted_dir.mkdir(parents=True, exist_ok=True)

    zip_files = list(raw_dir.glob("*.zip"))
    if not zip_files:
        logger.warning("No ZIP files found in %s.", raw_dir)
        return

    for zip_path in zip_files:
        logger.info("Processing ZIP: %s", zip_path.name)
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extracted_dir)
        logger.info("Extracted into: %s", extracted_dir)

    logger.info("All ZIP files extracted.")


if __name__ == "__main__":
    extract_zip()