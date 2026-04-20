"""
NMPA (国家药品监督管理局) Chinese drug database pipeline.
Source: https://www.nmpa.gov.cn / https://db.ouryao.com (public mirror)

Strategy:
  1. Query ouryao.com (comprehensive Chinese drug DB, public) via HTTP
  2. Parse results into Drug records
  3. Map to ATC codes via ingredient name matching
"""

import httpx
import logging
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
from sqlalchemy.orm import Session
from app.models.drug import Drug, ActiveIngredient, DrugIngredient, Country, PrescriptionStatus

log = logging.getLogger(__name__)

OURYAO_SEARCH = "https://db.ouryao.com/search.php"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def _fetch_ouryao(query: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        r = await client.get(OURYAO_SEARCH, params={"q": query}, headers=headers)
        r.raise_for_status()
        return r.text


async def search_condition_cn(condition_zh: str, db: Session, limit: int = 10) -> list[Drug]:
    """Search Chinese drugs by condition (in Chinese)."""
    try:
        html = await _fetch_ouryao(condition_zh)
        return _parse_results(html, db, limit)
    except Exception as e:
        log.error(f"NMPA/ouryao fetch error: {e}")
        # Fallback: return from our seeded DB
        return _search_db_by_indication(condition_zh, db, limit)


async def search_brand_cn(brand_zh: str, db: Session) -> list[Drug]:
    """Search Chinese drugs by brand name."""
    try:
        html = await _fetch_ouryao(brand_zh)
        return _parse_results(html, db, limit=5)
    except Exception as e:
        log.error(f"NMPA brand search error: {e}")
        return _search_db_by_name(brand_zh, db)


def _parse_results(html: str, db: Session, limit: int) -> list[Drug]:
    soup = BeautifulSoup(html, "lxml")
    drugs = []
    # ouryao result rows — adjust selectors if site changes
    rows = soup.select(".drug-item, .result-item, tr.drug-row")[:limit]

    for row in rows:
        name_el = row.select_one(".drug-name, .name, td:first-child a")
        ingredient_el = row.select_one(".ingredient, .zufen, td:nth-child(2)")
        mfr_el = row.select_one(".manufacturer, .qiye, td:nth-child(3)")

        if not name_el:
            continue

        brand_zh = name_el.get_text(strip=True)
        generic_zh = ingredient_el.get_text(strip=True) if ingredient_el else None
        manufacturer_zh = mfr_el.get_text(strip=True) if mfr_el else None

        drug = _upsert_cn_drug(brand_zh, generic_zh, manufacturer_zh, db)
        if drug:
            drugs.append(drug)

    db.commit()
    return drugs


def _upsert_cn_drug(
    brand_zh: str,
    generic_zh: str | None,
    manufacturer_zh: str | None,
    db: Session,
) -> Drug | None:
    existing = db.query(Drug).filter_by(brand_name=brand_zh, country=Country.CN).first()
    if existing:
        return existing

    drug = Drug(
        country=Country.CN,
        brand_name=brand_zh,
        brand_name_zh=brand_zh,
        generic_name_zh=generic_zh,
        manufacturer_zh=manufacturer_zh,
        source="NMPA/ouryao",
    )
    db.add(drug)
    db.flush()

    if generic_zh:
        ingredient = db.query(ActiveIngredient).filter_by(name_zh=generic_zh).first()
        if not ingredient:
            ingredient = ActiveIngredient(name_zh=generic_zh)
            db.add(ingredient)
            db.flush()
        db.add(DrugIngredient(drug_id=drug.id, ingredient_id=ingredient.id))

    return drug


def _search_db_by_indication(condition_zh: str, db: Session, limit: int) -> list[Drug]:
    return (
        db.query(Drug)
        .filter(
            Drug.country == Country.CN,
            Drug.indications_zh.contains(condition_zh),
        )
        .limit(limit)
        .all()
    )


def _search_db_by_name(name: str, db: Session) -> list[Drug]:
    return (
        db.query(Drug)
        .filter(
            Drug.country == Country.CN,
            Drug.brand_name.contains(name) | Drug.generic_name_zh.contains(name),
        )
        .limit(5)
        .all()
    )
