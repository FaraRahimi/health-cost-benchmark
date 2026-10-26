"""Acquire raw data for the health cost benchmark."""

from pathlib import Path
import time

import requests

VEKTIS_URL = "https://www.vektis.nl/vektisnl-assets/prd/storage/uploads/Docs%20per%20pagina/Open%20Data%20Bestanden/2024/Vektis%20Open%20Databestand%20Zorgverzekeringswet%202024%20-%20gemeente.csv"

RAW_DIR = Path("data/raw")


def download_vektis(force=False):
    """Download the Vektis 2024 municipality CSV to the raw data folder."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    file_path = RAW_DIR / "Vektis Open Databestand Zorgverzekeringswet 2024 - gemeente.csv"
    if file_path.exists() and not force:
        print(f"Skipped: {file_path} already exists")
        return file_path
    else:
        print("Downloading...")
        return file_path
    

download_vektis()