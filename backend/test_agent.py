"""End-to-end agent loop test with a stubbed LLM (no network).

Simulates a model that calls calculate(top_n) then produces a final text answer,
proving the agent loop + tool executor + message assembly all work together.
"""
import asyncio
import json

from app.agent import run_agent
from app.frame import Dataframe
from app.tools import TOOL_DEFINITIONS


class FakeLLM:
    def __init__(self):
        self.rounds = 0

    async def chat_with_tools(self, messages, tools, executor, max_rounds=3):
        df = executor.df
        out = executor.execute(
            "calculate",
            {"operation": "top_n", "value_column": "revenue", "n": 2, "group_by": "product"},
        )
        rows = ", ".join(f"{r['product']}={r['revenue']}" for r in out["rows"])
        chart = executor.execute(
            "chart",
            {
                "chart_type": "bar",
                "title": "Top products",
                "x_field": "product",
                "y_field": "revenue",
                "data_rows": out["rows"],
            },
        )
        json.dumps(chart)  # ensure serializable
        answer = f"Top products: {rows}. I used the calculate and chart tools."
        return {"content": answer, "tool_calls": []}


async def main():
    import io

    import pandas as pd

    sample = pd.DataFrame(
        {"product": ["a", "b", "a", "c", "b"], "revenue": [10, 20, 30, 40, 50]}
    )
    buf = io.StringIO()
    sample.to_csv(buf, index=False)
    df = Dataframe.from_csv_bytes("sales.csv", buf.getvalue().encode())

    result = await run_agent(FakeLLM(), df, "top products by revenue?")
    print("ANSWER:", result["content"])
    assert "a=40" in result["content"]
    assert len(TOOL_DEFINITIONS) == 3
    print("AGENT LOOP PASSED")


asyncio.run(main())
