from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..agent import run_agent
from ..llm import LLMClient, LLMError
from ..store import store

router = APIRouter()


class QueryRequest(BaseModel):
    dataset_id: str
    question: str = Field(..., min_length=1, max_length=2000)


class QueryResponse(BaseModel):
    answer: str


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    df = store.get(request.dataset_id)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found. Please re-upload.")

    try:
        llm = LLMClient()
    except LLMError as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        result = await run_agent(llm, df, request.question)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return QueryResponse(answer=result["content"])
