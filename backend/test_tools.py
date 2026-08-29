"""Quick sanity test for Dataframe + ToolExecutor (no LLM/network required).

Run:  .\.venv\Scripts\python -m test_tools
"""
import io

import pandas as pd

from app.frame import Dataframe
from app.tools import ToolExecutor, TOOL_DEFINITIONS

sample = pd.DataFrame(
    {
        "product": ["alpha", "beta", "alpha", "gamma", "beta", "alpha"],
        "revenue": [100, 200, 150, 300, 250, 400],
        "profit": [10, 40, 20, 60, 50, 80],
        "month": ["Jan", "Jan", "Feb", "Feb", "Mar", "Mar"],
    }
)

buf = io.StringIO()
sample.to_csv(buf, index=False)
df = Dataframe.from_csv_bytes("sample.csv", buf.getvalue().encode())

ex = ToolExecutor(df)

print("=== analyze_data ===")
print(ex.execute("analyze_data", {}))

print("\n=== calculate top_n revenue by product ===")
print(ex.execute("calculate", {"operation": "top_n", "value_column": "revenue", "n": 3, "group_by": "product"}))

print("\n=== calculate sum revenue grouped by month ===")
print(ex.execute("calculate", {"operation": "sum", "group_by": "month", "value_column": "revenue"}))

print("\n=== chart spec ===")
chart = ex.execute(
    "chart",
    {
        "chart_type": "bar",
        "title": "Revenue by product",
        "x_field": "product",
        "y_field": "revenue",
        "data_rows": [{"product": "alpha", "revenue": 650}],
    },
)
print(chart)

print("\n=== unknown tool ===")
print(ex.execute("nope", {}))

print("\n=== bad column ===")
print(ex.execute("calculate", {"operation": "sum", "group_by": "product", "value_column": "nope"}))

assert len(TOOL_DEFINITIONS) == 3, "expected 3 tool definitions"
print("\nALL SANITY CHECKS PASSED")
