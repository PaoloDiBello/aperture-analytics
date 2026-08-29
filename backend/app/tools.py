"""Tool definitions and executor for the AI agent.

The AI does not run arbitrary Python. Instead it can only call a small,
whitelisted set of tools (analyze, calculate, chart) described in OpenAPI
function-calling format. The `ToolExecutor` maps a tool call to a safe
operation on the stored Dataframe. This is the core of the "agent with tools"
architecture: the model decides which tools it needs, and our code performs
the actual data work.

Hallucination control:
  - The model never sees raw compute results it can invent; it only sees the
    curated tool outputs.
  - Numbers returned to the user come from the tool result, and we pin them
    into a structured "answer" block so the model must cite them rather than
    paraphrase from nothing.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

from .frame import Dataframe

TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "analyze_data",
            "description": (
                "Summarize a dataset: overall stats like row/column counts, "
                "column types, missing values, and basic per-column statistics "
                "(mean, min, max) for numeric columns. Use this first to "
                "understand the data before answering."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "columns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional; if omitted, summarize all columns.",
                    }
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": (
                "Compute a metric. Supported operations: 'sum' or 'mean' of a "
                "numeric value column grouped by a category column, or 'top_n' "
                "to return the top-n rows by a numeric column (optionally "
                "grouped). Returns a small table the caller can reason over."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["sum", "mean", "top_n"],
                        "description": "The aggregation to perform.",
                    },
                    "group_by": {
                        "type": "string",
                        "description": "Category column to group by (for sum/mean/top_n with grouping).",
                    },
                    "value_column": {
                        "type": "string",
                        "description": "Numeric column to aggregate.",
                    },
                    "n": {
                        "type": "integer",
                        "description": "Only for top_n: how many rows to return.",
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "Column to sort by.",
                    },
                    "ascending": {
                        "type": "boolean",
                        "description": "Sort direction.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Cap on number of rows to return.",
                    },
                },
                "required": ["operation"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "chart",
            "description": (
                "Declare chart intent so the frontend can render a visual. "
                "Returns a chart spec (type, data rows, x and y fields). The "
                "chart data should be derived from a prior calculate/analyze "
                "call, passed through verbatim. This tool does NOT render — it "
                "produces a serializable spec."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "enum": ["bar", "line", "pie", "scatter"],
                        "description": "Type of chart to render.",
                    },
                    "title": {"type": "string", "description": "Chart title."},
                    "x_field": {"type": "string", "description": "Category/axis field."},
                    "y_field": {"type": "string", "description": "Numeric/value field."},
                    "data_rows": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "description": "A row of {x_field: value, y_field: value}.",
                        },
                        "description": "The data points to plot, copied from a calculate result.",
                    },
                },
                "required": ["chart_type", "title", "x_field", "y_field", "data_rows"],
                "additionalProperties": False,
            },
        },
    },
]


def _as_chart_rows(df: Dataframe, x_field: str, y_field: str) -> List[Dict[str, Any]]:
    records = df.records(limit=100)
    rows = []
    for r in records:
        rows.append({x_field: r.get(x_field), y_field: r.get(y_field)})
    return rows


class ToolExecutor:
    def __init__(self, df: Dataframe):
        self.df = df

    def execute(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        handler: Optional[Callable[..., Dict[str, Any]]] = getattr(self, f"_tool_{name}", None)
        if handler is None:
            return {"error": f"Unknown tool: {name}"}
        try:
            return handler(**arguments)
        except KeyError as e:
            return {"error": f"Column not found: {e}. Available columns: {self.df.columns()}"}
        except Exception as e:  # noqa: BLE001 - surface tool errors to the model
            return {"error": f"Tool execution failed: {e}"}

    # ---- individual tools --------------------------------------------------

    def _tool_analyze_data(self, columns: Optional[List[str]] = None) -> Dict[str, Any]:
        df = self.df.df
        numeric = df.select_dtypes(include="number").columns.tolist()
        target = columns or list(df.columns)
        result = {
            "dataset": self.df.name,
            "rows": int(df.shape[0]),
            "columns": int(df.shape[1]),
            "column_types": self.df.dtypes(),
            "missing": self.df.missing_summary(),
            "numeric_columns": numeric,
            "column_stats": {},
        }
        for col in target:
            if col in numeric:
                s = df[col]
                result["column_stats"][col] = {
                    "mean": float(s.mean()) if pd_notna(s.mean()) else None,
                    "min": float(s.min()) if pd_notna(s.min()) else None,
                    "max": float(s.max()) if pd_notna(s.max()) else None,
                    "sum": float(s.sum()) if pd_notna(s.sum()) else None,
                }
            else:
                nunique = df[col].nunique()
                result["column_stats"][col] = {"unique_values": int(nunique)}
        return result

    def _tool_calculate(
        self,
        operation: str,
        group_by: Optional[str] = None,
        value_column: Optional[str] = None,
        n: Optional[int] = None,
        sort_by: Optional[str] = None,
        ascending: Optional[bool] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        if operation in ("sum", "mean"):
            if not value_column:
                return {"error": "value_column is required for sum/mean."}
            if group_by:
                out = (
                    self.df.groupby_sum(group_by, value_column)
                    if operation == "sum"
                    else self.df.groupby_mean(group_by, value_column)
                )
            else:
                scalar = self.df.df[value_column].sum() if operation == "sum" else self.df.df[value_column].mean()
                return {"operation": operation, "value_column": value_column, "result": float(scalar)}
            out = out.sort_by(value_column, ascending=False)
            rows = out.records(limit=limit)
            return {"operation": operation, "group_by": group_by, "value_column": value_column, "rows": rows}

        if operation == "top_n":
            if not value_column or n is None:
                return {"error": "value_column and n are required for top_n."}
            out = self.df.top_n(value_column, n=n, group_by=group_by)
            return {"operation": "top_n", "value_column": value_column, "n": n, "rows": out.records()}

        return {"error": f"Unknown operation: {operation}"}

    def _tool_chart(
        self,
        chart_type: str,
        title: str,
        x_field: str,
        y_field: str,
        data_rows: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        # We trust the model to pass through verbatim rows from a calculate
        # result, but we rebuild rows from the stored data when x/y fields are
        # real columns to guarantee chart data matches actual data.
        if x_field in self.df.df.columns and y_field in self.df.df.columns:
            rows = _as_chart_rows(self.df, x_field, y_field)
        else:
            records = self.df.records(limit=100)
            rows = []
            for r in records:
                rows.append({x_field: r.get(x_field), y_field: r.get(y_field)})
        return {
            "chart_type": chart_type,
            "title": title,
            "x_field": x_field,
            "y_field": y_field,
            "data_rows": rows,
        }


def pd_notna(value: Any) -> bool:
    import math

    return value is not None and not (isinstance(value, float) and math.isnan(value))
