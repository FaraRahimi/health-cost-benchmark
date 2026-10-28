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
| **Care-type contribution** | care type's cost gap / town's total cost gap x 100 | Which care types drive the extra cost; a slice can be negative if that care type is below expected |

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

## Health measure
**Self-rated health** (% of adults who rate their health as good or very good; higher = healthier). I chose it because it covers all kinds of health, so it matches total cost, the headline KPI. 
Anxiety or depression was set aside: it explains only the mental health slice, and specialist mental health costs are only about 90% complete in the Vektis data.

## Method (provisional)

## Cleaning decisions
- **Boundaries:** Vektis and CBS cover exactly the same 342 municipalities (2024 layout). `notebooks/02_clean.ipynb` Step 7 checks this with an `assert`.

## Findings
_To be filled in after analysis._

## Recommendations
_To be filled in after analysis._

## Limitations

## How to reproduce

## Project structure
