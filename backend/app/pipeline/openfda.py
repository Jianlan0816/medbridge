"""
openFDA drug label ingestion pipeline.
Pulls FDA-approved drugs with ingredients, dosage, and indications.
API docs: https://open.fda.gov/apis/drug/label/
"""

import os
import httpx
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from sqlalchemy.orm import Session
from app.models.drug import Drug, ActiveIngredient, DrugIngredient, Country, PrescriptionStatus

log = logging.getLogger(__name__)

OPENFDA_BASE = "https://api.fda.gov/drug/label.json"
API_KEY = os.getenv("OPENFDA_API_KEY", "")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def _fetch(params: dict) -> dict:
    headers = {}
    if API_KEY:
        params["api_key"] = API_KEY
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(OPENFDA_BASE, params=params)
        r.raise_for_status()
        return r.json()


async def ingest_condition(condition_en: str, db: Session, limit: int = 20) -> list[Drug]:
    """
    Search openFDA for drugs treating a given condition.
    Returns list of Drug objects (upserted into DB).
    """
    params = {
        "search": f'indications_and_usage:"{condition_en}"',
        "limit": limit,
    }
    try:
        data = await _fetch(params)
    except Exception as e:
        log.error(f"openFDA fetch error: {e}")
        return []

    results = data.get("results", [])
    drugs = []
    for item in results:
        drug = _parse_label(item, db)
        if drug:
            drugs.append(drug)

    db.commit()
    return drugs


async def ingest_brand(brand_name: str, db: Session) -> list[Drug]:
    """Search openFDA for a specific brand name."""
    params = {
        "search": f'openfda.brand_name:"{brand_name}"',
        "limit": 5,
    }
    try:
        data = await _fetch(params)
    except Exception as e:
        log.error(f"openFDA fetch error for brand {brand_name}: {e}")
        return []

    results = data.get("results", [])
    drugs = []
    for item in results:
        drug = _parse_label(item, db)
        if drug:
            drugs.append(drug)
    db.commit()
    return drugs


def _parse_label(item: dict, db: Session) -> Drug | None:
    """Parse a single openFDA label result into a Drug record."""
    openfda = item.get("openfda", {})
    brand_names = openfda.get("brand_name", [])
    generic_names = openfda.get("generic_name", [])

    if not brand_names and not generic_names:
        return None

    brand_name = brand_names[0] if brand_names else generic_names[0]
    generic_name = generic_names[0] if generic_names else None

    # Deduplicate by source_id
    source_id = item.get("id", brand_name)
    existing = db.query(Drug).filter_by(source_id=source_id, country=Country.US).first()
    if existing:
        return existing

    # Prescription status
    rx_otc = openfda.get("product_type", [""])[0].lower()
    if "otc" in rx_otc:
        rx_status = PrescriptionStatus.otc
    elif "prescription" in rx_otc:
        rx_status = PrescriptionStatus.prescription
    else:
        rx_status = PrescriptionStatus.unknown

    # Indications
    indications_raw = item.get("indications_and_usage", [""])
    indications = indications_raw[0][:500] if indications_raw else ""

    drug = Drug(
        country=Country.US,
        brand_name=brand_name,
        brand_name_en=brand_name,
        generic_name=generic_name,
        manufacturer=", ".join(openfda.get("manufacturer_name", [])),
        prescription_status=rx_status,
        indications=indications,
        dosage_form=", ".join(openfda.get("dosage_form", [])),
        source="openFDA",
        source_id=source_id,
    )
    db.add(drug)
    db.flush()  # get drug.id

    # Active ingredients
    active_ingredients = openfda.get("substance_name", [])
    for ing_name in active_ingredients:
        ing_name_clean = ing_name.strip().lower()
        ingredient = db.query(ActiveIngredient).filter_by(name_en=ing_name_clean).first()
        if not ingredient:
            ingredient = ActiveIngredient(name_en=ing_name_clean)
            db.add(ingredient)
            db.flush()

        db.add(DrugIngredient(drug_id=drug.id, ingredient_id=ingredient.id))

    return drug
