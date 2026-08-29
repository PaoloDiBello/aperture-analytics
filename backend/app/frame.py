"""Dataframe wrapper around pandas.

We deliberately wrap pandas in a small abstraction so the agent's tools talk
to a stable, safe interface instead of raw pandas. This keeps in-memory data
handling predictable and makes the tool boundary explicit (the single source
of truth for what the AI can do to the data).
"""
from __future__ import annotations

import io
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

MAX_CELLS_FOR_CONTEXT = 2000


class Dataframe:
    def __init__(self, name: str, df: pd.DataFrame):
        self.name = name
        self.df = df

    @classmethod
    def from_csv_bytes(cls, name: str, content: bytes) -> "Dataframe":
        df = pd.read_csv(io.BytesIO(content))
        return cls(name, df)

    # ---- schema / shape helpers -------------------------------------------
    @property
    def shape(self) -> Tuple[int, int]:
        return self.df.shape

    def columns(self) -> List[str]:
        return list(self.df.columns)

    def dtypes(self) -> Dict[str, str]:
        return {c: str(t) for c, t in self.df.dtypes.items()}

    def sample_rows(self, n: int = 10) -> List[Dict[str, Any]]:
        return self.df.head(n).where(pd.notnull(self.df), None).to_dict(orient="records")

    def missing_summary(self) -> Dict[str, int]:
        return self.df.isna().sum().to_dict()

    # ---- safe execution of tool operations ---------------------------------
    def groupby_sum(self, by: str, value: str) -> "Dataframe":
        """Group data by a column and sum a numeric column. Returns a new frame."""
        result = self.df.groupby(by)[value].sum().reset_index()
        return Dataframe(f"agg_{by}_sum_{value}", result)

    def groupby_mean(self, by: str, value: str) -> "Dataframe":
        result = self.df.groupby(by)[value].mean().reset_index()
        return Dataframe(f"agg_{by}_mean_{value}", result)

    def sort_by(self, column: str, ascending: bool = False, limit: Optional[int] = None) -> "Dataframe":
        result = self.df.sort_values(column, ascending=ascending)
        if limit is not None:
            result = result.head(limit)
        return Dataframe(f"sorted_{column}", result.reset_index(drop=True))

    def top_n(self, column: str, n: int = 5, group_by: Optional[str] = None) -> "Dataframe":
        """Return top-n rows by a numeric column, optionally grouped."""
        if group_by:
            result = self.groupby_sum(group_by, column).df
        else:
            result = self.df.copy()
        result = result.sort_values(column, ascending=False).head(n).reset_index(drop=True)
        return Dataframe(f"top_{n}_{column}", result)

    def records(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        data = self.df
        if limit is not None:
            data = data.head(limit)
        return data.where(pd.notnull(data), None).to_dict(orient="records")

    # ---- context / prompt helpers ------------------------------------------
    def context_block(self) -> str:
        """A compact textual representation of the dataset for the AI prompt."""
        lines = [
            f"Dataset: {self.name}",
            f"Shape: {self.shape[0]} rows x {self.shape[1]} columns",
            "Columns & types: " + ", ".join(f"{c} ({t})" for c, t in self.dtypes().items()),
            "",
            "Missing values: " + ", ".join(f"{c}={v}" for c, v in self.missing_summary().items()),
            "",
            "Sample (first up to 10 rows):",
        ]
        sample = self.sample_rows(n=10)
        for row in sample:
            lines.append(str(row))
        return "\n".join(lines)

    def preview(self) -> Dict[str, Any]:
        """Frontend-facing preview payload (never the whole dataset)."""
        return {
            "name": self.name,
            "rows": self.shape[0],
            "columns": self.shape[1],
            "column_names": self.columns(),
            "dtypes": self.dtypes(),
            "preview": self.sample_rows(n=10),
        }
