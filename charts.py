"""Make the five benchmark charts from the tables that pipeline.py saves."""

from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

PROCESSED_DIR = Path("data/processed")
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


if __name__ == "__main__":
    # Make the figures folder if it does not exist yet (a fresh clone)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # Tables saved by pipeline.py
    rates = pd.read_csv(PROCESSED_DIR / "reference_rates.csv")

    chart_cost_by_age(rates, FIGURES_DIR / "01_cost_by_age.png")
