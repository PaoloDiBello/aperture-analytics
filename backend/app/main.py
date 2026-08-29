from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import upload, query
from app.config import settings

app = FastAPI(title="Aperture Analytics API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(query.router, prefix="/api", tags=["query"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
