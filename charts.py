"""Make the five benchmark charts from the tables that pipeline.py saves."""

from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.patches import Patch

from pipeline import weighted_national_health, add_segments

PROCESSED_DIR = Path("data/processed")
OUTPUT_DIR = Path("outputs")
FIGURES_DIR = Path("figures")


def chart_cost_by_age(rates, path):
    """Take the national reference rates; save a line chart of cost per insured-year by age, one line per sex."""
    # One table per sex, so each gets its own line
    men = rates[rates["geslacht"] == "M"]
    women = rates[rates["geslacht"] == "V"]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(men["age_from"], men["rate"], color="#2a78d6", linewidth=2, label="Men")
    ax.plot(women["age_from"], women["rate"], color="#eb6834", linewidth=2, label="Women")

    # Title states the finding; axes say what and in which unit
    ax.set_title("Care cost per person rises steeply with age, so towns must be compared fairly", loc="left")
    ax.set_xlabel("Age (start of 5-year band)")
    ax.set_ylabel("Cost per insured-year (EUR)")
    ax.yaxis.set_major_formatter(lambda v, pos: f"{v:,.0f}")

    # Quiet grid and frame, so the lines stand out
    ax.grid(axis="y", color="#e5e4e0", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False)

    # Source line under the chart
    fig.text(0.01, -0.02, "Source: Vektis 2024", fontsize=8, color="#52514e")

    # Save (tight keeps the source line in the image), then close so the figure does not stay in memory
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


def top_15_lists(big_towns):
    """Take the big towns; return the top 15 by cost index, the top 15 by excess, and the town names on both lists."""
    # Same ranking as notebook Step 4: size rule already applied in big_towns
    top_index = big_towns.sort_values("cost_index", ascending=False).head(15)
    top_excess = big_towns.sort_values("excess", ascending=False).head(15)
    on_both = set(top_index["gemeentenaam"]) & set(top_excess["gemeentenaam"])
    return top_index, top_excess, on_both


def chart_top15_index(big_towns, path):
    """Take the big towns; save a bar chart of the 15 highest cost indexes, towns also top 15 in euros highlighted."""
    top_index, top_excess, on_both = top_15_lists(big_towns)

    # Reverse the order so the highest bar is at the top (barh draws from the bottom up)
    chart2 = top_index.iloc[::-1]
    # Towns that are also in the top 15 by euros get the strong colour, the rest a quiet grey
    colours2 = ["#2a78d6" if name in on_both else "#c3c2b7" for name in chart2["gemeentenaam"]]

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(chart2["gemeentenaam"].str.title(), chart2["cost_index"], color=colours2)

    # Reference line at 100 = exactly as expected for the town's age and sex mix
    ax.axvline(100, color="#52514e", linewidth=1, linestyle="--")

    # Value at the end of each bar, so nobody has to read it off the axis
    for y, value in enumerate(chart2["cost_index"]):
        ax.text(value + 1, y, f"{value:.1f}", va="center", fontsize=8, color="#52514e")

    ax.set_title("13 of the 15 towns furthest above expected are in South Limburg or the north-east", loc="left", fontsize=11, pad=24)
    ax.set_xlabel("Cost index (100 = expected for the town's age and sex mix)")
    ax.set_xlim(0, 135)
    ax.spines[["top", "right"]].set_visible(False)

    # Legend for the two colours (made by hand, because the bars are one series)
    ax.legend(handles=[Patch(color="#2a78d6", label="Also top 15 by excess euros"),
                       Patch(color="#c3c2b7", label="Top 15 by index only")],
              frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=8)

    fig.text(0.01, -0.02, "Source: Vektis 2024. Towns with 10,000+ insured-years only.", fontsize=8, color="#52514e")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


def chart_top15_excess(big_towns, path):
    """Take the big towns; save a bar chart of the 15 highest excess costs in EUR million, towns also top 15 by index highlighted."""
    top_index, top_excess, on_both = top_15_lists(big_towns)

    chart3 = top_excess.iloc[::-1]
    colours3 = ["#2a78d6" if name in on_both else "#c3c2b7" for name in chart3["gemeentenaam"]]
    excess_m = chart3["excess"] / 1_000_000

    fig, ax = plt.subplots(figsize=(8, 6))
    # Vektis writes 's-Gravenhage as "S GRAVENHAGE"; show the usual name
    ax.barh(chart3["gemeentenaam"].str.title().replace("S Gravenhage", "The Hague"), excess_m, color=colours3)

    # Value at the end of each bar, in millions
    for y, value in enumerate(excess_m):
        ax.text(value + 2, y, f"€{value:.0f}M", va="center", fontsize=8, color="#52514e")

    ax.set_title("In euros, the big cities lead: Rotterdam alone is €186M above expected", loc="left", fontsize=11)
    ax.set_xlabel("Excess cost (actual minus expected, EUR million)")
    ax.set_xlim(0, 210)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(handles=[Patch(color="#2a78d6", label="Also top 15 by cost index"),
                       Patch(color="#c3c2b7", label="Top 15 by euros only")],
              frameon=False, loc="lower right", fontsize=8)

    fig.text(0.01, -0.02, "Source: Vektis 2024. Towns with 10,000+ insured-years only.", fontsize=8, color="#52514e")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


def chart_drivers_top5(priority_list, care_type_town, path):
    """Take the priority list and the care-type table; save a heatmap of care-type indexes for the top 5 priority towns."""
    top5 = priority_list.head(5)
    # One row per town, one column per care type, cost_index in the cells
    heat = care_type_town[care_type_town["Key"].isin(top5["Key"])].pivot(
        index="gemeentenaam", columns="care_type", values="cost_index"
    )
    # Keep the priority order (Groningen first) and nicer names
    heat = heat.loc[top5["gemeentenaam"]]
    heat.index = heat.index.str.title()
    # Leave out care abroad: it depends on distance to the border, not on anything a contract review can change (Finding 5b)
    heat = heat.drop(columns="Care abroad")

    fig, ax = plt.subplots(figsize=(10, 3.8))
    # Diverging colours: blue below 100, white at 100, red above; capped at 50 and 150 so one extreme cell cannot wash out the rest
    norm = TwoSlopeNorm(vmin=50, vcenter=100, vmax=150)
    image = ax.imshow(heat.clip(50, 150), cmap="RdBu_r", norm=norm, aspect="auto")

    # Town names on the left, care types along the bottom
    ax.set_yticks(range(len(heat.index)), heat.index)
    ax.set_xticks(range(len(heat.columns)), heat.columns, rotation=35, ha="right")

    # The real index in every cell (not the capped one)
    for row in range(heat.shape[0]):
        for col in range(heat.shape[1]):
            ax.text(col, row, f"{heat.iloc[row, col]:.0f}", ha="center", va="center", fontsize=8, color="#0b0b0b")

    fig.colorbar(image, ax=ax, label="Cost index (100 = expected)", shrink=0.8)
    ax.set_title("Mental health is far above expected in 4 of the top 5 priority towns", loc="left", fontsize=11)
    fig.text(0.01, -0.3, "Source: Vektis 2024. Care abroad left out. Colours capped at 50 and 150; numbers show the real index.", fontsize=8, color="#52514e")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


def chart_health_vs_cost(big_towns, national_health, path):
    """Take the big towns with segments and national health; save a scatter of health against cost index, one dot per town."""
    fig, ax = plt.subplots(figsize=(9, 6.5))

    # The two high-cost segments get a colour, the two others stay grey
    segment_colours = {
        "Unexplained high cost": "#2a78d6",
        "Explained high cost": "#eb6834",
        "Baseline": "#c3c2b7",
        "Efficient": "#c3c2b7",
    }
    ax.scatter(big_towns["health_value"], big_towns["cost_index"],
               s=10 + big_towns["aantal_verzekerdejaren"] / 2500,
               c=big_towns["segment"].map(segment_colours),
               alpha=0.75, edgecolors="white", linewidths=0.8)

    # Dividing lines: national health and an index of 100
    ax.axvline(national_health, color="#52514e", linewidth=1, linestyle="--")
    ax.axhline(100, color="#52514e", linewidth=1, linestyle="--")

    # Name each corner (segment) in plain words
    ax.text(0.99, 0.98, "Unexplained high cost\n(healthier, still expensive)", transform=ax.transAxes, ha="right", va="top", fontsize=9, color="#2a78d6", fontweight="bold")
    ax.text(0.22, 0.98, "Explained high cost\n(less healthy)", transform=ax.transAxes, ha="left", va="top", fontsize=9, color="#eb6834", fontweight="bold")
    ax.text(0.01, 0.02, "Efficient\n(less healthy, not expensive)", transform=ax.transAxes, ha="left", va="bottom", fontsize=9, color="#52514e")
    ax.text(0.99, 0.02, "Baseline\n(healthier, not expensive)", transform=ax.transAxes, ha="right", va="bottom", fontsize=9, color="#52514e")

    # Label a few towns the story mentions
    for name in ["HEERLEN", "GRONINGEN", "UTRECHT", "AMSTERDAM", "ROTTERDAM"]:
        town = big_towns[big_towns["gemeentenaam"] == name].iloc[0]
        ax.annotate(name.title(), (town["health_value"], town["cost_index"]), xytext=(6, 4),
                    textcoords="offset points", fontsize=8, color="#0b0b0b")

    ax.set_title("Less healthy towns cost more (Spearman -0.55), yet 29 healthier towns still cost more than expected", loc="left", fontsize=11)
    ax.set_xlabel(f"Adults rating their health good or very good (%); dashed line = national {national_health:.1f}%")
    ax.set_ylabel("Cost index (100 = expected)")
    ax.spines[["top", "right"]].set_visible(False)

    fig.text(0.01, -0.02, "Source: Vektis 2024, CBS Gezondheidsmonitor 2024. 329 towns with 10,000+ insured-years; dot size = insured-years.", fontsize=8, color="#52514e")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


if __name__ == "__main__":
    # Make the figures folder if it does not exist yet (a fresh clone)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # Tables saved by pipeline.py
    rates = pd.read_csv(PROCESSED_DIR / "reference_rates.csv")
    town_kpis = pd.read_csv(PROCESSED_DIR / "town_benchmark.csv")
    care_type_town = pd.read_csv(PROCESSED_DIR / "care_type_benchmark.csv")
    priority_list = pd.read_csv(OUTPUT_DIR / "priority_list.csv")

    # National health and segments: the same functions as pipeline.py, so the numbers cannot drift apart
    national_health = weighted_national_health(town_kpis)
    big_towns = add_segments(town_kpis, national_health)

    chart_cost_by_age(rates, FIGURES_DIR / "01_cost_by_age.png")
    chart_top15_index(big_towns, FIGURES_DIR / "02_top15_cost_index.png")
    chart_top15_excess(big_towns, FIGURES_DIR / "03_top15_excess.png")
    chart_drivers_top5(priority_list, care_type_town, FIGURES_DIR / "04_drivers_top5.png")
    chart_health_vs_cost(big_towns, national_health, FIGURES_DIR / "05_health_vs_cost.png")
