"""
Auto analysis: scans every CSV under results/, computes a Pearson
correlation matrix between numeric factors and accuracy, and writes a
markdown summary to results/report.md.
"""
from __future__ import annotations

import os
import glob
from typing import List, Optional

import numpy as np
import pandas as pd


# Factors we know are continuous-ish; we only correlate numeric columns
# against accuracy to avoid choking on string-valued factors.
NUMERIC_FACTOR_HINTS = {
    "total_tokens",
    "depth",
    "noise",
    "turns_count",
    "instruction_distance",
    "query_distance",
    "fragment_count",
    "needle_fragment_index",
    "gap_tokens",
    "output_pressure",
    "max_tokens",
    "semantic_distractor_count",
}


def _is_numeric_series(s: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(s)


def _coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Best-effort coerce object columns that look numeric (lists, tuples)."""
    for col in df.columns:
        if _is_numeric_series(df[col]):
            continue
        if col in NUMERIC_FACTOR_HINTS:
            try:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            except Exception:
                pass
    return df


def _summarize_factor(df: pd.DataFrame, col: str) -> str:
    if not _is_numeric_series(df[col]):
        # Categorical: show value -> mean accuracy.
        grouped = df.groupby(col)["accuracy"].agg(["mean", "count"])
        lines = [f"| {col} | mean accuracy | n |", "|---|---|---|"]
        for idx, row in grouped.iterrows():
            lines.append(f"| {idx} | {row['mean']:.3f} | {int(row['count'])} |")
        return "\n".join(lines)

    grouped = df.groupby(col)["accuracy"].mean()
    return (
        f"- **{col}** numeric, range "
        f"[{df[col].min():.3g}..{df[col].max():.3g}], "
        f"mean accuracy: {grouped.mean():.3f}"
    )


def analyze(csv_path: str, output_path: Optional[str] = None) -> str:
    df = pd.read_csv(csv_path)
    if "accuracy" not in df.columns:
        raise ValueError(f"{csv_path} has no 'accuracy' column")

    df = _coerce_numeric(df)

    # Keep only numeric columns that have at least 2 distinct values.
    numeric_cols = [
        c for c in df.columns
        if c != "accuracy" and _is_numeric_series(df[c]) and df[c].nunique(dropna=True) > 1
    ]

    corr = df[numeric_cols + ["accuracy"]].corr() if numeric_cols else pd.DataFrame()

    lines: List[str] = []
    name = os.path.splitext(os.path.basename(csv_path))[0]
    lines.append(f"# Auto Analysis Report — `{name}`")
    lines.append("")
    lines.append(f"- Rows: **{len(df)}**")
    lines.append(f"- Mean accuracy: **{df['accuracy'].mean():.3f}**")
    lines.append(f"- Std accuracy: **{df['accuracy'].std():.3f}**")
    lines.append("")

    if not numeric_cols:
        lines.append("> No numeric factors found; only categorical breakdown is available.")
    else:
        lines.append("## Correlation matrix (factor vs accuracy)")
        lines.append("")
        header = "| factor | Pearson r | |r| |"
        sep = "|---|---|---|"
        lines.append(header)
        lines.append(sep)
        for col in numeric_cols:
            r = corr.loc[col, "accuracy"]
            lines.append(f"| {col} | {r:+.3f} | {abs(r):.3f} |")
        lines.append("")

        # Highlight the most influential factor (by |r|), excluding self.
        ranked = sorted(
            ((c, corr.loc[c, "accuracy"]) for c in numeric_cols),
            key=lambda kv: abs(kv[1]),
            reverse=True,
        )
        if ranked:
            top, top_r = ranked[0]
            lines.append(
                f"> Most influential factor: **{top}** (r = {top_r:+.3f})."
            )
        lines.append("")

    lines.append("## Per-factor breakdown")
    lines.append("")
    factor_cols = [c for c in df.columns if c not in {"accuracy", "response", "scenario"}]
    for col in factor_cols:
        if df[col].nunique(dropna=False) <= 1:
            continue
        lines.append(_summarize_factor(df, col))
        lines.append("")

    text = "\n".join(lines)
    if output_path is None:
        output_path = os.path.join(os.path.dirname(csv_path), f"{name}_report.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    return text


def analyze_all(results_dir: str = "results", output_path: Optional[str] = None) -> str:
    csvs = sorted(glob.glob(os.path.join(results_dir, "experiment_*.csv")))
    if not csvs:
        raise FileNotFoundError(f"No experiment_*.csv files under {results_dir}")

    sections: List[str] = ["# NeedleRust — Aggregate Report", ""]
    for csv in csvs:
        sections.append(analyze(csv))
        sections.append("\n---\n")

    text = "\n".join(sections)
    if output_path is None:
        output_path = os.path.join(results_dir, "report.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    return text


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate correlation-matrix reports for experiment CSVs.")
    parser.add_argument("--results-dir", default="results", help="Directory containing experiment_*.csv files.")
    parser.add_argument("--output", default=None, help="Output markdown path.")
    args = parser.parse_args()
    out = analyze_all(args.results_dir, args.output)
    print(out)
