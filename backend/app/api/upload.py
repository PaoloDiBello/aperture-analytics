from fastapi import APIRouter, HTTPException, UploadFile, File

from ..frame import Dataframe
from ..store import store

router = APIRouter()


@router.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file.")

    # Reasonable guard on file size to keep the in-memory store small.
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 20MB).")

    try:
        df = Dataframe.from_csv_bytes(file.filename, content)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")

    dataset_id = store.put(df)
    return {"dataset_id": dataset_id, "preview": df.preview()}
