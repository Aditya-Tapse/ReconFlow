from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app import models  # noqa: F401 ensures all models are registered before create_all
from app.api.invoices import router as invoices_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ReconFlow - AP Invoice Processing")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(invoices_router)


@app.get("/health")
def health():
    return {"status": "ok"}
