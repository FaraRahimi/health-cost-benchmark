# Health Cost Benchmark: Dutch municipalities, 2024

> Fictional stakeholder brief; the data is real and public.

## Executive summary
_To be written at the end._

## The brief
- **Stakeholder:** Regional Healthcare Strategy Manager at a Dutch health insurer (fictional), responsible for care purchasing and planning.
- **Decision:** which municipalities and care types to prioritise for further investigation or targeted programmes in the next purchasing and planning cycle. The analysis shows *where* spending is unusual, not automatically *why*.
- **Business question:** Which Dutch municipalities had higher basic-insurance costs per person in 2024 than expected for their age and sex mix?
  - Which care types make up most of the extra cost?
  - Is the extra cost larger where residents are less healthy?

## Metric definitions
All costs are basic-insurance (Zvw) claims paid for 2024, per **insured-year**
(one person insured for a full year).

| Metric | Formula | How to read it |
|---|---|---|
| **Actual cost per person** | town's total cost / town's insured-years | Real paid bills, in € |
| **Expected cost per person** | national cost per insured-year for each age-sex group, applied to the town's own age-sex mix | What the town would cost if it were "average" for its population |
| **Cost gap (€)** | (actual - expected) per person x town's insured-years | Total extra euros; 0 = as expected |
| **Cost index** (headline) | actual / expected x 100 | 100 = as expected; 120 = 20% more than expected |
| **Care-type cost index** | care type's actual / expected x 100, per town | Which care types are far above expected; same scale as the cost index |
| **Care-type excess (€)** | care type's actual - expected, per town | Where the extra euros sit; the top 2 per town are the "drivers" in the priority list |

**Worked example:** a town has 10 young residents (national rate €1,000) and 10 older
residents (national rate €5,000). Expected = (10 x 1,000 + 10 x 5,000) / 20 = **€3,000**
per person. If it actually costs €3,600 per person, the cost index is
3,600 / 3,000 x 100 = **120**.

**Analysis, not a KPI:** is the cost index higher where self-rated health is lower?

## Data sources
1. **Vektis Open Databestand Zorgverzekeringswet 2024 - gemeente.**
   Basic-insurance (Zvw) costs for 2024, split into 26 care types, per municipality, sex and five-year age band, with insured people and insured-years.
   12,992 rows x 31 columns, semicolon-separated CSV.
   
   Link: [Vektis open databestanden](https://www.vektis.nl/zorgprisma/open-databestanden)
   
   Documentation: Vektis bijsluiter (leaflet) 2011-2024.
   
   Credit: bron: Vektis. Free for personal and research use; no commercial use.
2. **CBS Gezondheidsmonitor 2024, table 86137NED.**
   Health survey results for adults (18+) per municipality, with 95% margins.
   
   Used: self-rated health (% good or very good).
   
   Link: [CBS StatLine 86137NED](https://opendata.cbs.nl/#/CBS/nl/dataset/86137NED/table), accessed through the CBS open data API.
   
   Credit: Bron: GGD'en, RIVM en CBS.

**Why 2024.** It is the most recent year Vektis publishes (checked November 2026; the next file is announced for mid-2027), because claims for a year keep arriving and being settled for months after it ends. The CBS Gezondheidsmonitor covers the same year, so cost and health describe the same period. Which towns cost more than expected changes slowly, so two-year-old data still answers the purchasing question.

## Health measure
**Self-rated health** (% of adults who rate their health as good or very good; higher = healthier). I chose it because it covers all kinds of health, so it matches total cost, the headline KPI. 
Anxiety or depression was set aside: it explains only the mental health slice, and specialist mental health costs are only about 90% complete in the Vektis data.

## Method (provisional)

## Cleaning decisions
Every decision is written out in full (found, did, why, rejected) in `notebooks/02_clean.ipynb`. `pipeline.py` runs the decided steps; one command, `python pipeline.py`, Every decision is written out in full (found, did, why, rejected) in `notebooks/02_clean.ipynb`. `pipeline.py` runs the decided steps; one command, `python pipeline.py`, rebuilds the clean tables, the analysis and the priority list from the raw data.


- **Privacy bucket removed.** One unlabelled row holds groups under 10 people and people with unknown sex, age or municipality: 2.2% of people but 0.3% of cost. It cannot be placed in any municipality.
- **Negative cells kept.** 2 of about 338,000 cells (Uitgeest, Twenterand), each under 0.01% of that town's cost. They are real corrections, and keeping them keeps totals equal to the official Vektis figures.
- **Care abroad kept.** 0.6% of all cost, but 18% in Sluis and 5 to 10% in other border towns. Excluding it would make those towns look cheaper than they are.
- **Age band as a number.** `age_from` (0, 5 ... 90), so age bands sort correctly.
- **10 care-type groups.** The 26 Vektis cost columns are mapped to 10 groups in `data/manual/care_type_groups.csv`. An assert checks the groups add up to the total in every row.
- **Name matching.** Vektis has only names, CBS has codes. A matching key (capitals, accents removed) matched 329 of 342; the other 13 are fixed by hand in `data/manual/name_fixes.csv`. Asserts check every row has a code.
- **Boundaries.** Vektis and CBS cover exactly the same 342 municipalities (2024 layout), checked by an assert.
- **CBS reshaped.** Adults (18+) and self-rated health only, one row per municipality, with the value and its 95% interval (`health_value`, `health_low`, `health_high`).
- **Missing health values kept empty.** Schiermonnikoog and Vlieland have no health figure. They stay in the cost benchmark and are left out only of the cost-versus-health comparison.

## Limitations
- CBS health figures cover adults (18+) only, while Vektis cost covers all ages.
- Care abroad is incomplete in the Vektis data (foreign bills arrive late), so border towns' true cost is probably higher than shown.
- Health figures are survey estimates. Small municipalities have wide 95% intervals, so an extreme value there may be noise.


## Findings
_To be filled in after analysis._

## Recommendations
_To be filled in after analysis._

## How to reproduce

Tested with Python 3.13 on macOS. You need internet access for the CBS download.

1. **Clone the repo and set up a virtual environment.**
   ```bash
   git clone https://github.com/FaraRahimi/health-cost-benchmark.git
   cd health-cost-benchmark
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Download the Vektis file by hand.** Vektis blocks scripted downloads, so this is
   the one manual step. Download
   [Vektis Open Databestand Zorgverzekeringswet 2024 - gemeente](https://www.vektis.nl/vektisnl-assets/prd/storage/uploads/Docs%20per%20pagina/Open%20Data%20Bestanden/2024/Vektis%20Open%20Databestand%20Zorgverzekeringswet%202024%20-%20gemeente.csv)
   and save it, with its name unchanged, as
   `data/raw/Vektis Open Databestand Zorgverzekeringswet 2024 - gemeente.csv`.
   If the file is missing, `pipeline.py` stops and prints these same instructions.
3. **Run the pipeline, then the charts.**
   ```bash
   python pipeline.py
   python charts.py
   ```
   `pipeline.py` downloads the two CBS tables into `data/raw/` (skipped if they are
   already there), cleans both sources, runs the benchmark and saves the priority list.
   Every step checks itself with asserts, so a wrong number stops the run instead of
   reaching the results.

**What you get:** `outputs/priority_list.csv` (the 15 priority municipalities) and five
charts in `figures/`. The notebooks in `notebooks/` show the same steps with every
decision explained; they read the files the pipeline makes, so run the pipeline first.

## Project structure

| Path | What it holds | Made by |
|---|---|---|
| `pipeline.py` | Download, clean and analyse; saves the priority list | hand |
| `charts.py` | The five charts, one function each | hand |
| `notebooks/01_explore.ipynb` | First look at the raw data | hand |
| `notebooks/02_clean.ipynb` | Every cleaning decision: found, did, why | hand |
| `notebooks/03_analyse.ipynb` | The benchmark step by step, with findings | hand |
| `data/raw/` | Vektis and CBS source files (not in git) | you (Vektis) and the pipeline (CBS) |
| `data/manual/` | Hand-made inputs: care-type groups, name fixes, suggested focus per town | hand |
| `data/processed/` | Clean and analysis tables (not in git) | the pipeline |
| `outputs/priority_list.csv` | The deliverable: 15 municipalities to review | the pipeline |
| `figures/` | The five charts as PNG | `charts.py` |
