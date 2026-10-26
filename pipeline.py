"""Acquire raw data for the health cost benchmark."""

from pathlib import Path
import time

import requests

VEKTIS_URL = "https://www.vektis.nl/vektisnl-assets/prd/storage/uploads/Docs%20per%20pagina/Open%20Data%20Bestanden/2024/Vektis%20Open%20Databestand%20Zorgverzekeringswet%202024%20-%20gemeente.csv"

RAW_DIR = Path("data/raw")

print(RAW_DIR.exists())