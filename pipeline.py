"""Acquire and clean raw data for the health cost benchmark."""

from pathlib import Path
import time

import requests
import pandas as pd

VEKTIS_URL = "https://www.vektis.nl/vektisnl-assets/prd/storage/uploads/Docs%20per%20pagina/Open%20Data%20Bestanden/2024/Vektis%20Open%20Databestand%20Zorgverzekeringswet%202024%20-%20gemeente.csv"
CBS_URL = "https://opendata.cbs.nl/ODataFeed/odata/86137NED"

RAW_DIR = Path("data/raw")
MANUAL_DIR = Path("data/manual")
PROCESSED_DIR = Path("data/processed")
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
        try:
            response = requests.get(url, params=params, headers=HEADERS, timeout=60)
        except requests.exceptions.ConnectionError:
            raise SystemExit("Cannot reach CBS. Check your internet connection.")
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
        try:
            response = requests.get(url, params=params, headers=HEADERS, timeout=60)
        except requests.exceptions.ConnectionError:
            raise SystemExit("Cannot reach CBS. Check your internet connection.")
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


def load_vektis():
    """Load the raw Vektis 2024 municipality file (semicolon-separated)."""
    file_path = check_vektis()
    vektis = pd.read_csv(file_path, sep=";")
    return vektis
    

def drop_privacy_bucket(vektis):
    """Remove the privacy bucket: the one row with no municipality name."""
    vektis = vektis[vektis["gemeentenaam"].notna()]
    assert len(vektis) == 12991, f"Expected 12,991 rows after the bucket, got {len(vektis)}"
    return vektis


def add_age_number(vektis):
    """Add age_from: the lower age of each band as a number, so bands sort 0, 5 ... 90."""
    vektis["age_from"] = vektis["leeftijdsklasse"].str.extract(r"(\d+)").astype(int)
    return vektis


def add_care_types(vektis):
    """Add one cost column per care-type group and cost_total, and check they add up."""
    groups = pd.read_csv(MANUAL_DIR / "care_type_groups.csv")
    cost_columns = vektis.filter(like="kosten").columns
    group_names = groups["group"].unique()

    # For each group: find its cost columns in the mapping and add them up per row
    for group in group_names:
        cols = groups.loc[groups["group"] == group, "column"]
        vektis[group] = vektis[cols].sum(axis=1)

    vektis["cost_total"] = vektis[cost_columns].sum(axis=1)

    # The groups must add up to the total of all 26 cost columns (less than 1 cent apart)
    difference = (vektis[group_names].sum(axis=1) - vektis["cost_total"]).abs().max()
    assert difference < 0.01, f"Care-type groups do not add up: off by {difference:.2f}"
    return vektis


def make_match_key(names):
    """Matching key for town names: capitals, accents removed. Used on both sides."""
    return (
        names
        .str.upper()
        .str.normalize("NFKD")
        .str.encode("ascii", errors="ignore")
        .str.decode("ascii")
    )


def match_names(vektis):
    """Give every Vektis row its CBS municipality code (Key), matched on the town name."""
    regions = pd.read_csv(fetch_cbs_regions())
    name_fixes = pd.read_csv(MANUAL_DIR / "name_fixes.csv")

    # One matching key per side, made by the same rule
    vektis["match_key"] = make_match_key(vektis["gemeentenaam"])
    regions["match_key"] = make_match_key(regions["Title"])

    # One row per town: match on the key, then fill the 13 manual fixes
    towns = vektis[["match_key", "gemeentenaam"]].drop_duplicates()
    towns = pd.merge(towns, regions[["match_key", "Key"]], on="match_key", how="left")
    towns = pd.merge(towns, name_fixes, left_on="gemeentenaam", right_on="vektis_name", how="left")
    towns["Key"] = towns["Key"].fillna(towns["cbs_code"])
    assert towns["Key"].notna().all(), "Some towns have no CBS code: check name_fixes.csv"
    assert towns["Key"].nunique() == 342, "Two towns share one CBS code"

    # Give every Vektis row its town's code
    vektis = pd.merge(vektis, towns[["match_key", "Key"]], on="match_key", how="left")
    assert len(vektis) == 12991, "The merge added rows"
    assert vektis["Key"].notna().all(), "Some Vektis rows have no CBS code"
    return vektis


def load_cbs_health():
    """Load CBS self-rated health for adults (18+): one row per town, value plus 95% interval."""
    cbs_health = pd.read_csv(fetch_cbs())
    cbs_health = cbs_health[cbs_health["Leeftijd"] == 10000]
    cbs_health = cbs_health[["RegioS", "Marges", "ErvarenGezondheidGoedZeerGoed_1"]]
    cbs_health = cbs_health.pivot(index="RegioS", columns="Marges", values="ErvarenGezondheidGoedZeerGoed_1")
    cbs_health = cbs_health.reset_index()
    cbs_health = cbs_health.rename(columns={
        "MW00000": "health_value",
        "MOG0095": "health_low",
        "MBG0095": "health_high",
    })
    assert len(cbs_health) == 342, f"Expected 342 towns, got {len(cbs_health)}"
    assert cbs_health["RegioS"].nunique() == 342, "A town appears twice"
    # Schiermonnikoog and Vlieland have no health figure; the rows are kept on purpose
    assert cbs_health["health_value"].isna().sum() == 2, "The number of towns without a health value changed"
    return cbs_health


def check_boundaries(vektis, cbs_health):
    """Stop if Vektis and CBS do not cover exactly the same 342 municipalities."""
    vektis_codes = set(vektis["Key"])
    cbs_codes = set(cbs_health["RegioS"])
    assert vektis_codes == cbs_codes, (
        f"Only in Vektis: {vektis_codes - cbs_codes}. Only in CBS: {cbs_codes - vektis_codes}"
    )
    assert len(vektis_codes) == 342, f"Expected 342 municipalities, got {len(vektis_codes)}"


def save_clean(vektis, cbs_health):
    """Save the two clean tables to data/processed/."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    vektis.to_csv(PROCESSED_DIR / "vektis_clean.csv", index=False)
    cbs_health.to_csv(PROCESSED_DIR / "cbs_health_clean.csv", index=False)
    print(f"Saved: {PROCESSED_DIR} (vektis_clean.csv {vektis.shape}, cbs_health_clean.csv {cbs_health.shape})")


def clean():
    """Run every cleaning step in order, from the raw files to the two clean tables."""
    vektis = load_vektis()
    vektis = drop_privacy_bucket(vektis)
    vektis = add_age_number(vektis)
    vektis = add_care_types(vektis)
    vektis = match_names(vektis)
    cbs_health = load_cbs_health()
    check_boundaries(vektis, cbs_health)
    save_clean(vektis, cbs_health)


if __name__ == "__main__":
    clean()
    