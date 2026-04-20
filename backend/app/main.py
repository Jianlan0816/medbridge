"""
MedBridge FastAPI backend.

Endpoints:
  POST /api/search/condition  — Mode 1: condition → drug recommendations (US + CN)
  POST /api/search/brand      — Mode 2: brand name → cross-country equivalent
  GET  /api/drugs/{id}        — Get full drug details
  GET  /health                — Health check
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import logging

from app.database import init_db, get_db, SessionLocal
from app.pipeline.seed import run as seed_db
from app.agents import run_condition_search, run_brand_translation
from app.models.drug import SearchLog

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    log.info("Initializing database...")
    init_db()
    db = SessionLocal()
    try:
        seed_db(db)
    finally:
        db.close()
    log.info("MedBridge ready.")
    yield
    # Shutdown (nothing to clean up)


app = FastAPI(
    title="MedBridge API",
    description="Bilingual drug translation and safety agent — US ↔ China",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response schemas ────────────────────────────────────────────────

class ConditionSearchRequest(BaseModel):
    condition: str = Field(..., example="type 2 diabetes", description="Medical condition in English or Chinese")
    from_country: str = Field("US", pattern="^(US|CN)$")
    to_country: str = Field("CN", pattern="^(US|CN)$")


class BrandSearchRequest(BaseModel):
    brand_name: str = Field(..., example="Ozempic", description="Drug brand or generic name")
    from_country: str = Field("US", pattern="^(US|CN)$")
    to_country: str = Field("CN", pattern="^(US|CN)$")
    other_drugs: list[str] = Field(default=[], description="Other drugs the patient takes (for DDI check)")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "MedBridge"}


@app.post("/api/search/condition")
async def search_by_condition(req: ConditionSearchRequest, db: Session = Depends(get_db)):
    """
    Mode 1: Patient searches by medical condition.
    Returns drug recommendations for both countries with equivalents.
    """
    log.info(f"Condition search: '{req.condition}' {req.from_country}→{req.to_country}")

    db.add(SearchLog(
        mode="condition",
        query=req.condition,
        from_country=req.from_country,
        to_country=req.to_country,
    ))
    db.commit()

    result = await run_condition_search(
        condition=req.condition,
        from_country=req.from_country,
        to_country=req.to_country,
        db=db,
    )

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@app.post("/api/search/brand")
async def search_by_brand(req: BrandSearchRequest, db: Session = Depends(get_db)):
    """
    Mode 2: Patient enters their current drug brand name.
    Returns the equivalent in the destination country + DDI check.
    """
    log.info(f"Brand search: '{req.brand_name}' {req.from_country}→{req.to_country}")

    db.add(SearchLog(
        mode="brand",
        query=req.brand_name,
        from_country=req.from_country,
        to_country=req.to_country,
    ))
    db.commit()

    result = await run_brand_translation(
        brand_name=req.brand_name,
        from_country=req.from_country,
        to_country=req.to_country,
        other_drugs=req.other_drugs,
        db=db,
    )

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@app.get("/api/drugs/{drug_id}")
def get_drug(drug_id: int, db: Session = Depends(get_db)):
    """Get full details for a specific drug by ID."""
    from app.models.drug import Drug
    drug = db.get(Drug, drug_id)
    if not drug:
        raise HTTPException(status_code=404, detail="Drug not found")
    from app.tools.drug_tools import _drug_detail
    return _drug_detail(drug)
