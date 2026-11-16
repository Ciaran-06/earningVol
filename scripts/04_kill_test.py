"""Kill test: reproduce every result in NOTES.md with one command.

Pre-registration commit: 985103f (criterion, sample, pricing and robustness fixed before any P&L).
Checks (known answers, identities, sizes) live in notebooks/strat_tester.py; run those first.

Run from the repo root:  uv run python scripts/04_kill_test.py
Writes the tables to reports/kill_test/ as CSV (for the write-up and blog charts).
"""
from pathlib import Path

import pandas as pd

from earning_vol.io import load_derived
from earning_vol.strategy import kill_sample, rule_pnl, summarise, linear_oos, cost_table

ROBUSTNESS_START = "2013-01-01"          # pre-registered post-weeklies cut-off (NOTES.md)
OUT_DIR = Path(__file__).resolve().parents[1] / "reports" / "kill_test"


def rules_table(sample: pd.DataFrame) -> pd.DataFrame:
    """One row per rule: n, mean, std, t (P&L at bid/ask, per traded event)."""
    rules = rule_pnl(sample)
    return pd.DataFrame([summarise(p) for p in rules.values()], index=list(rules.keys()))


def show(title: str, table: pd.DataFrame) -> None:
    print(f"\n================ {title} ================")
    print(table.round(4).to_string())


def main() -> None:
    events = load_derived("events")
    sample = kill_sample(events)
    sample_2013 = sample[sample["report_date"] >= ROBUSTNESS_START]

    tables = {
        "rules_full": rules_table(sample),
        "rules_from_2013": rules_table(sample_2013),
        "linear_model": pd.DataFrame([linear_oos(sample)], index=["linear_oos"]),
        "costs_full": cost_table(sample),
        "costs_from_2013": cost_table(sample_2013),
    }

    show("H2 - Rules at bid/ask: full sample", tables["rules_full"])
    show(f"Robustness - Rules at bid/ask: from {ROBUSTNESS_START}", tables["rules_from_2013"])
    show("H1 - Linear model (train 2010-18, test 2019-23)", tables["linear_model"])
    show("Cost diagnostics: full sample", tables["costs_full"])
    show(f"Cost diagnostics: from {ROBUSTNESS_START}", tables["costs_from_2013"])

    # verdict, applying the pre-registered criterion mechanically
    rules = tables["rules_full"]
    h1 = tables["linear_model"].loc["linear_oos", "r2_vs_mean"] > 0
    h2 = ((rules["mean"] > 0) & (rules["t"] > 2)).any()
    print("\n================ Verdict ================")
    print(f"H1 (out-of-sample R^2 vs training mean > 0):   {'pass' if h1 else 'fail'}")
    print(f"H2 (any rule with mean > 0 and t > 2):          {'pass' if h2 else 'fail'}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(OUT_DIR / f"{name}.csv")
    print(f"\nTables saved to {OUT_DIR}")


if __name__ == "__main__":
    main()