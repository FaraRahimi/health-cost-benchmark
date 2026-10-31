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
OUTPUT_DIR = Path("outputs")
HEADERS = {"User-Agent": "health-cost-benchmark (portfolio project)"}

# The 10 care-type groups made in clean (add_care_types), used by the care-type benchmark
CARE_TYPES = ["Hospital care", "Pharmacy", "GP care", "Mental health", "Nursing and rehabilitation",
              "Paramedical", "Aids and dental", "Maternity", "Care abroad", "Transport and other"]

# Size rule: towns with fewer insured-years than this are too small to rank fairly
MIN_INSURED_YEARS = 10_000


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


def reference_rates(vektis):
    """Take the clean Vektis table and return the table of 38 national rates (sex x age band)."""
    # National totals per sex and age group: sum cost and insured-years over all towns
    rates = vektis.groupby(["geslacht", "age_from"])[["cost_total", "aantal_verzekerdejaren"]].sum()
    # Reference rate: national cost per insured-year, per sex and age group
    rates["rate"] = rates["cost_total"] / rates["aantal_verzekerdejaren"]
    # Move sex and age out of the index into normal columns, so they can be merged later
    rates_flat = rates.reset_index()
    # Stop if the table is not 2 sexes x 19 age bands
    assert len(rates_flat) == 38, f"Expected 38 sex x age groups, got {len(rates_flat)}"
    return rates_flat


def town_index(vektis, rates_flat):
    """Take the clean Vektis table and the national rates; return one row per town (342) with the cost KPIs."""
    # Give every Vektis row the national rate of its own sex and age group
    vektis_rated = pd.merge(vektis, rates_flat[["geslacht", "age_from", "rate"]], on=["geslacht", "age_from"], how="left")
    assert len(vektis_rated) == 12991, "The merge added rows"
    assert vektis_rated["rate"].notna().all(), "Some rows have no rate"

    # Expected cost per row: insured-years x national rate of that sex and age group
    vektis_rated["expected"] = vektis_rated["aantal_verzekerdejaren"] * vektis_rated["rate"]

    # One row per town: add up actual cost, expected cost and insured-years over all sex and age groups
    vektis_town = vektis_rated.groupby(["Key", "gemeentenaam"])[["cost_total", "expected", "aantal_verzekerdejaren"]].sum().reset_index()
    assert len(vektis_town) == 342, f"Expected 342 towns, got {len(vektis_town)}"

    # KPIs per town: cost per insured-year (actual and expected), cost index, and excess in euros
    vektis_town["actual_per_person"] = vektis_town["cost_total"] / vektis_town["aantal_verzekerdejaren"]
    vektis_town["expected_per_person"] = vektis_town["expected"] / vektis_town["aantal_verzekerdejaren"]
    vektis_town["cost_index"] = vektis_town["cost_total"] / vektis_town["expected"] * 100
    vektis_town["excess"] = vektis_town["cost_total"] - vektis_town["expected"]

    # Checksum: the whole country compared with itself must come out at exactly expected
    assert round(vektis_town["cost_total"].sum()) == round(vektis_town["expected"].sum()), "Expected total does not equal actual total"
    return vektis_town


def care_type_index(vektis):
    """Take the clean Vektis table; return one row per town and care type (3,420) with cost index and excess."""
    # Reshape wide to long: one row per town x sex x age x care type, with that care type's cost
    vektis_long = vektis.melt(id_vars=["Key", "gemeentenaam", "geslacht", "age_from", "aantal_verzekerdejaren"],
                              value_vars=CARE_TYPES, var_name="care_type", value_name="cost")

    # National rate per care type, sex and age group: total cost / total insured-years
    rates_ct = vektis_long.groupby(["care_type", "geslacht", "age_from"])[["cost", "aantal_verzekerdejaren"]].sum()
    rates_ct["rate"] = rates_ct["cost"] / rates_ct["aantal_verzekerdejaren"]
    rates_ct_flat = rates_ct.reset_index()

    # Give every row the national rate of its own care type, sex and age group, then its expected cost
    vektis_long_rated = pd.merge(vektis_long, rates_ct_flat[["care_type", "geslacht", "age_from", "rate"]],
                                 on=["care_type", "geslacht", "age_from"], how="left")
    vektis_long_rated["expected"] = vektis_long_rated["aantal_verzekerdejaren"] * vektis_long_rated["rate"]

    # One row per town and care type: add up actual cost, expected cost and insured-years
    care_type_town = vektis_long_rated.groupby(["Key", "gemeentenaam", "care_type"])[["cost", "expected", "aantal_verzekerdejaren"]].sum().reset_index()
    assert len(care_type_town) == 342 * 10, f"Expected 3,420 rows, got {len(care_type_town)}"

    # KPIs per town and care type: cost index and excess in euros
    care_type_town["cost_index"] = care_type_town["cost"] / care_type_town["expected"] * 100
    care_type_town["excess"] = care_type_town["cost"] - care_type_town["expected"]

    # Checksum: for each care type, the whole country must come out at excess 0
    excess_by_type = care_type_town.groupby("care_type")["excess"].sum()
    assert (excess_by_type.round() == 0).all(), "A care type does not balance to 0"
    return care_type_town


def add_health(vektis_town, cbs_health):
    """Take the town table and the clean CBS health table; return one row per town (342) with cost KPIs and health."""
    # Same municipality codes, different column names: Key (Vektis) and RegioS (CBS). how="left" keeps all 342 towns
    town_kpis = pd.merge(vektis_town, cbs_health, left_on="Key", right_on="RegioS", how="left")

    # Check: still 342 towns, and only the 2 islands without a health value
    assert len(town_kpis) == 342, f"Expected 342 towns, got {len(town_kpis)}"
    assert town_kpis["health_value"].isna().sum() == 2, "Expected only Schiermonnikoog and Vlieland to be missing"
    return town_kpis


def add_size_rule(town_kpis):
    """Take the town table; return it with passes_size_rule (True when the town has at least MIN_INSURED_YEARS insured-years)."""
    # Towns below the threshold are too small to rank fairly: one costly patient can move their index
    town_kpis["passes_size_rule"] = town_kpis["aantal_verzekerdejaren"] >= MIN_INSURED_YEARS

    # Check: 13 towns fall below the threshold
    small = (~town_kpis["passes_size_rule"]).sum()
    assert small == 13, f"Expected 13 small towns, got {small}"
    return town_kpis


def weighted_national_health(town_kpis):
    """Take the town table; return national self-rated health (%), weighted by insured-years like the cost index."""
    # Only towns with a health value (the 2 islands have none)
    has_health = town_kpis.dropna(subset=["health_value"])
    # Average of town health values, with big towns counting more (weights = insured-years)
    return (has_health["health_value"] * has_health["aantal_verzekerdejaren"]).sum() / has_health["aantal_verzekerdejaren"].sum()


def add_segments(town_kpis, national_health):
    """Take the town table and national health; return the 329 big towns, each with one of four segments."""
    # Only towns that pass the size rule; .copy() so new columns go on this table, not on town_kpis
    big_towns = town_kpis[town_kpis["passes_size_rule"]].copy()
    assert big_towns["health_value"].notna().all(), "A big town has no health value"

    # Two yes/no questions per town: costs above national? healthier than national?
    big_towns["high_cost"] = big_towns["cost_index"] > 100
    big_towns["healthy"] = big_towns["health_value"] >= national_health

    # One label per town from the two yes/no columns
    big_towns["segment"] = ""
    big_towns.loc[big_towns["healthy"] & big_towns["high_cost"], "segment"] = "Unexplained high cost"
    big_towns.loc[~big_towns["healthy"] & big_towns["high_cost"], "segment"] = "Explained high cost"
    big_towns.loc[~big_towns["healthy"] & ~big_towns["high_cost"], "segment"] = "Efficient"
    big_towns.loc[big_towns["healthy"] & ~big_towns["high_cost"], "segment"] = "Baseline"

    # Check: every town has a label, 329 in total, 29 unexplained
    assert (big_towns["segment"] != "").all(), "A town has no segment"
    assert len(big_towns) == 329, f"Expected 329 big towns, got {len(big_towns)}"
    unexplained = (big_towns["segment"] == "Unexplained high cost").sum()
    assert unexplained == 29, f"Expected 29 unexplained towns, got {unexplained}"
    return big_towns


def make_priority_list(big_towns, care_type_town, national_health):
    """Take the big towns, the care-type table and national health; return the 15-town priority list."""
    # Unexplained high-cost towns, highest excess euros first (the ranking rule)
    unexplained = big_towns[big_towns["segment"] == "Unexplained high cost"].sort_values("excess", ascending=False).copy()

    # Confidence: clear when even the bottom of the CBS survey range is above national health
    unexplained["confidence"] = "borderline"
    unexplained.loc[unexplained["health_low"] > national_health, "confidence"] = "clear"
    assert (unexplained["confidence"] == "clear").sum() == 9, "Expected 9 clear towns"

    # Top 15; reset_index so the row labels run 0 to 14
    priority = unexplained.head(15).reset_index(drop=True)

    # The 2 care types with the most excess euros in each priority town
    priority_drivers = care_type_town[care_type_town["Key"].isin(priority["Key"])].sort_values(
        ["Key", "excess"], ascending=[True, False]
    ).groupby("Key").head(2)
    assert len(priority_drivers) == 30, "Expected 30 rows: 15 towns x 2 drivers"

    # Turn the 2 rows per town into 2 columns, and add them to the priority list
    driver_1 = priority_drivers.groupby("Key").nth(0)[["Key", "care_type"]].rename(columns={"care_type": "top_driver_1"})
    driver_2 = priority_drivers.groupby("Key").nth(1)[["Key", "care_type"]].rename(columns={"care_type": "top_driver_2"})
    priority = pd.merge(priority, driver_1, on="Key", how="left")
    priority = pd.merge(priority, driver_2, on="Key", how="left")
    assert priority[["top_driver_1", "top_driver_2"]].notna().all().all(), "A town is missing a driver"

    # One hand-written action per town, kept in data/manual (judgment, not calculation)
    focus = pd.read_csv(MANUAL_DIR / "suggested_focus.csv")
    priority = pd.merge(priority, focus[["Key", "suggested_focus"]], on="Key", how="left")
    assert priority["suggested_focus"].notna().all(), "A priority town has no suggested focus: update data/manual/suggested_focus.csv"

    # Rank 1 to 15, only the columns the insurer needs, readable numbers
    priority["rank"] = priority.index + 1
    columns = ["rank", "Key", "gemeentenaam", "aantal_verzekerdejaren", "health_value", "cost_index",
               "excess", "confidence", "top_driver_1", "top_driver_2", "suggested_focus"]
    priority_list = priority[columns].copy()
    priority_list = priority_list.round({"health_value": 1, "cost_index": 1})
    priority_list["aantal_verzekerdejaren"] = priority_list["aantal_verzekerdejaren"].round().astype(int)
    priority_list["excess"] = priority_list["excess"].round().astype(int)
    assert len(priority_list) == 15
    return priority_list


def save_priority_list(priority_list):
    """Take the priority list; save it to outputs/priority_list.csv and check the saved file."""
    # Make the outputs folder if it does not exist yet (a fresh clone)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "priority_list.csv"
    priority_list.to_csv(path, index=False)

    # Read the file back to prove it was written correctly
    check = pd.read_csv(path)
    assert len(check) == 15, "Expected 15 towns in the saved file"
    assert check["rank"].tolist() == list(range(1, 16)), "Ranks should run 1 to 15"
    assert check["suggested_focus"].notna().all()
    print(f"Saved: {path} ({check.shape})")


def analyse():
    """Run the analysis on the clean tables, in order, and save the priority list."""
    # Load the two clean tables made by clean()
    vektis = pd.read_csv(PROCESSED_DIR / "vektis_clean.csv")
    cbs_health = pd.read_csv(PROCESSED_DIR / "cbs_health_clean.csv")

    # Town benchmark: national rates, town KPIs, health, size rule
    rates_flat = reference_rates(vektis)
    town_kpis = town_index(vektis, rates_flat)
    town_kpis = add_health(town_kpis, cbs_health)
    town_kpis = add_size_rule(town_kpis)

    # Segments: is the high cost explained by health?
    national_health = weighted_national_health(town_kpis)
    big_towns = add_segments(town_kpis, national_health)

    # Care-type benchmark, for the drivers
    care_type_town = care_type_index(vektis)

    # The deliverable
    priority_list = make_priority_list(big_towns, care_type_town, national_health)
    save_priority_list(priority_list)


if __name__ == "__main__":
    clean()
    analyse()