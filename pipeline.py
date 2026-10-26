"""Acquire raw data for the health cost benchmark."""

from pathlib import Path
import time

import requests
import pandas as pd

VEKTIS_URL = "https://www.vektis.nl/vektisnl-assets/prd/storage/uploads/Docs%20per%20pagina/Open%20Data%20Bestanden/2024/Vektis%20Open%20Databestand%20Zorgverzekeringswet%202024%20-%20gemeente.csv"
CBS_URL = "https://opendata.cbs.nl/ODataFeed/odata/86137NED"

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


def fetch_cbs(force=False):
    """Fetch the CBS 2024 health table for municipalities."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    file_path = RAW_DIR / "cbs_86137NED_gemeenten.csv"
    if file_path.exists() and not force:
        print(f"Skipped...: {file_path} already exists")
        return file_path
    url = CBS_URL + "/TypedDataSet"
    params = {"$filter": "startswith(RegioS, 'GM')", "$format": "json"}
    all_rows = []

    # CBS ODataFeed pages at 10,000 rows and gives the next page in odata.nextLink.
    while url:
        response = requests.get(url, params=params, headers=HEADERS, timeout=60)
        if response.status_code != 200:
            raise SystemExit(f"CBS request failed: status {response.status_code}")
        data = response.json()
        all_rows.extend(data["value"])
        url = data.get("odata.nextLink")
        params = None
        time.sleep(1)
    
    df = pd.DataFrame(all_rows)
    df.to_csv(file_path, index=False)
    print(f"Saved: {file_path} ({len(all_rows)} rows)")
    return file_path


def fetch_cbs_regions(force=False):
    """Fetch the CBS code list that maps each municipality code to its name."""

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    file_path = RAW_DIR / "cbs_86137NED_regions.csv"
    if file_path.exists() and not force:
        print(f"Skipped... {file_path} already exists")
        return file_path

    url = CBS_URL + "/RegioS"
    params = {"$filter": "startswith(Key, 'GM')", "$format": "json"}
    all_rows = []

    # CBS ODataFeed pages at 10,000 rows and gives the next page in odata.nextLink.
    while url:
        response = requests.get(url, params=params, headers=HEADERS, timeout=60)
        if response.status_code != 200:
            raise SystemExit(f"CBS request failed: status {response.status_code}")
        data = response.json()
        all_rows.extend(data["value"])
        url = data.get("odata.nextLink")
        params = None
        time.sleep(1)
    df = pd.DataFrame(all_rows)
    df.to_csv(file_path, index=False)
    print(f"Saved: {file_path} ({len(all_rows)} rows)")
    return file_path


check_vektis()
fetch_cbs()
fetch_cbs_regions()