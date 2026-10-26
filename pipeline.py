"""Acquire raw data for the health cost benchmark."""

from pathlib import Path
import time

import requests

VEKTIS_URL = "https://www.vektis.nl/vektisnl-assets/prd/storage/uploads/Docs%20per%20pagina/Open%20Data%20Bestanden/2024/Vektis%20Open%20Databestand%20Zorgverzekeringswet%202024%20-%20gemeente.csv"
CBS_URL = "https://opendata.cbs.nl/ODataApi/odata/86137NED"

RAW_DIR = Path("data/raw")
HEADERS = {"User-Agent": "health-cost-benchmark (portfolio project)"}


def check_vektis():
    """Check that the Vektis 2024 municipality CSV is in the raw data folder.

    Vektis blocks scripted downloads (403), so this file is downloaded by hand.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    file_path = RAW_DIR / "Vektis Open Databestand Zorgverzekeringswet 2024 - gemeente.csv"
    if file_path.exists():
        print(f"Found: {file_path}")
        return file_path
    else:
        raise SystemExit(f"The file is missing, Vektis blocks automated downloads\n download it by hand from {VEKTIS_URL}\n save it as {file_path}")



def fetch_cbs():
    """Fetch the CBS 2024 health table for municipalities."""
    params = {"$filter": "startswith(RegioS, 'GM')", "$format": "json"}
    response = requests.get(CBS_URL + "/TypedDataSet", params=params, headers=HEADERS, timeout=60)
    rows = response.json()["value"]
    print(len(rows))
    return rows


check_vektis()
fetch_cbs()