"""
Tool definitions for the MedBridge agent.
Each tool maps to a Claude tool_use block and a real async function.

Tools:
  search_drugs_by_condition  — find drugs for a condition in US or CN
  search_drugs_by_brand      — look up a drug by brand name
  find_equivalents           — find cross-country equivalents via ATC bridge
  check_interactions         — check DDI between two or more ingredients
  get_drug_detail            — get full info on a specific drug
  translate_drug_name        — translate brand/generic name EN↔ZH
"""

import json
from sqlalchemy.orm import Session
from app.models.drug import Drug, ActiveIngredient, DrugInteraction, Country, DDISeverity


# ── Tool schemas (sent to Claude) ─────────────────────────────────────────────

TOOLS = [
    {
        "name": "search_drugs_by_condition",
        "description": (
            "Search for drugs used to treat a medical condition in a specific country (US or CN). "
            "Returns a list of brand names, generic names, prescription status, and dosage info."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "condition": {"type": "string", "description": "Medical condition in English (e.g. 'type 2 diabetes', 'hypertension', 'headache')"},
                "country": {"type": "string", "enum": ["US", "CN"], "description": "Country to search drugs for"},
            },
            "required": ["condition", "country"],
        },
    },
    {
        "name": "search_drugs_by_brand",
        "description": (
            "Look up a specific drug by its brand name or generic name. "
            "Works for both English and Chinese names. Returns full drug details."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Brand name or generic name (e.g. 'Ozempic', '诺和泰', 'metformin')"},
                "country": {"type": "string", "enum": ["US", "CN", "any"], "description": "Country to search in"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "find_equivalents",
        "description": (
            "Find equivalent drugs in another country based on the same active ingredient (ATC code). "
            "This is the core translation function — given a US drug, find its Chinese equivalent and vice versa."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "drug_name": {"type": "string", "description": "Drug brand or generic name to find equivalents for"},
                "from_country": {"type": "string", "enum": ["US", "CN"]},
                "to_country": {"type": "string", "enum": ["US", "CN"]},
            },
            "required": ["drug_name", "from_country", "to_country"],
        },
    },
    {
        "name": "check_interactions",
        "description": (
            "Check for drug-drug interactions between two or more active ingredients or drug names. "
            "Returns severity (contraindicated/major/moderate/minor) and clinical description."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "drug_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of 2+ drug names (brand or generic) to check interactions between",
                },
            },
            "required": ["drug_names"],
        },
    },
    {
        "name": "get_drug_detail",
        "description": "Get complete bilingual details for a specific drug including dosage, warnings, and prescription status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "drug_name": {"type": "string"},
                "country": {"type": "string", "enum": ["US", "CN", "any"]},
            },
            "required": ["drug_name"],
        },
    },
]


# ── Tool execution ─────────────────────────────────────────────────────────────

async def execute_tool(tool_name: str, tool_input: dict, db: Session) -> str:
    """Dispatch tool call and return JSON string result."""
    if tool_name == "search_drugs_by_condition":
        result = _search_by_condition(tool_input["condition"], tool_input["country"], db)
    elif tool_name == "search_drugs_by_brand":
        result = _search_by_brand(tool_input["name"], tool_input.get("country", "any"), db)
    elif tool_name == "find_equivalents":
        result = _find_equivalents(tool_input["drug_name"], tool_input["from_country"], tool_input["to_country"], db)
    elif tool_name == "check_interactions":
        result = _check_interactions(tool_input["drug_names"], db)
    elif tool_name == "get_drug_detail":
        result = _get_detail(tool_input["drug_name"], tool_input.get("country", "any"), db)
    else:
        result = {"error": f"Unknown tool: {tool_name}"}

    return json.dumps(result, ensure_ascii=False, indent=2)


# ── Tool implementations ──────────────────────────────────────────────────────

def _search_by_condition(condition: str, country: str, db: Session) -> dict:
    country_enum = Country.US if country == "US" else Country.CN
    drugs = (
        db.query(Drug)
        .filter(
            Drug.country == country_enum,
            Drug.indications.ilike(f"%{condition}%") |
            Drug.indications_zh.ilike(f"%{condition}%")
        )
        .limit(8)
        .all()
    )
    return {"country": country, "condition": condition, "drugs": [_drug_summary(d) for d in drugs]}


def _search_by_brand(name: str, country: str, db: Session) -> dict:
    q = db.query(Drug).filter(
        Drug.brand_name.ilike(f"%{name}%") |
        Drug.brand_name_en.ilike(f"%{name}%") |
        Drug.brand_name_zh.ilike(f"%{name}%") |
        Drug.generic_name.ilike(f"%{name}%") |
        Drug.generic_name_zh.ilike(f"%{name}%")
    )
    if country != "any":
        country_enum = Country.US if country == "US" else Country.CN
        q = q.filter(Drug.country == country_enum)
    drugs = q.limit(5).all()
    return {"query": name, "drugs": [_drug_detail(d) for d in drugs]}


def _find_equivalents(drug_name: str, from_country: str, to_country: str, db: Session) -> dict:
    from_enum = Country.US if from_country == "US" else Country.CN
    to_enum = Country.US if to_country == "US" else Country.CN

    # Find source drug
    source = (
        db.query(Drug)
        .filter(
            Drug.country == from_enum,
            Drug.brand_name.ilike(f"%{drug_name}%") |
            Drug.brand_name_en.ilike(f"%{drug_name}%") |
            Drug.brand_name_zh.ilike(f"%{drug_name}%") |
            Drug.generic_name.ilike(f"%{drug_name}%") |
            Drug.generic_name_zh.ilike(f"%{drug_name}%")
        )
        .first()
    )

    if not source:
        return {"error": f"Drug '{drug_name}' not found in {from_country} database"}

    # Find equivalents via ATC code (same active ingredient)
    equivalents = []

    # 1. ATC code match
    if source.atc_code:
        atc_matches = (
            db.query(Drug)
            .filter(Drug.country == to_enum, Drug.atc_code == source.atc_code)
            .all()
        )
        equivalents.extend(atc_matches)

    # 2. Ingredient name match (fallback)
    if not equivalents:
        for link in source.ingredients:
            ing = link.ingredient
            if not ing:
                continue
            ing_drugs = (
                db.query(Drug)
                .join(Drug.ingredients)
                .join(ActiveIngredient, DrugIngredient.ingredient_id == ActiveIngredient.id)
                .filter(
                    Drug.country == to_enum,
                    (ActiveIngredient.name_en == ing.name_en) |
                    (ActiveIngredient.name_zh == ing.name_zh)
                )
                .all()
            )
            equivalents.extend(ing_drugs)

    # Deduplicate
    seen = set()
    unique = []
    for d in equivalents:
        if d.id not in seen:
            seen.add(d.id)
            unique.append(d)

    return {
        "source_drug": _drug_detail(source),
        "from_country": from_country,
        "to_country": to_country,
        "equivalents": [_drug_detail(d) for d in unique],
        "match_count": len(unique),
    }


def _check_interactions(drug_names: list[str], db: Session) -> dict:
    # Resolve drug names to ingredients
    ingredients = []
    for name in drug_names:
        drug = (
            db.query(Drug)
            .filter(
                Drug.brand_name.ilike(f"%{name}%") |
                Drug.brand_name_en.ilike(f"%{name}%") |
                Drug.generic_name.ilike(f"%{name}%") |
                Drug.generic_name_zh.ilike(f"%{name}%")
            )
            .first()
        )
        if drug:
            for link in drug.ingredients:
                if link.ingredient and link.ingredient not in ingredients:
                    ingredients.append(link.ingredient)
        else:
            # try direct ingredient name
            ing = db.query(ActiveIngredient).filter(
                ActiveIngredient.name_en.ilike(f"%{name}%") |
                ActiveIngredient.name_zh.ilike(f"%{name}%")
            ).first()
            if ing:
                ingredients.append(ing)

    interactions = []
    for i in range(len(ingredients)):
        for j in range(i + 1, len(ingredients)):
            a, b = ingredients[i], ingredients[j]
            ddi = db.query(DrugInteraction).filter(
                ((DrugInteraction.ingredient_a_id == a.id) & (DrugInteraction.ingredient_b_id == b.id)) |
                ((DrugInteraction.ingredient_a_id == b.id) & (DrugInteraction.ingredient_b_id == a.id))
            ).first()
            if ddi:
                interactions.append({
                    "drug_a": a.name_en,
                    "drug_b": b.name_en,
                    "severity": ddi.severity.value,
                    "description": ddi.description,
                    "description_zh": ddi.description_zh,
                })

    return {
        "checked_drugs": drug_names,
        "resolved_ingredients": [i.name_en for i in ingredients],
        "interactions": interactions,
        "safe": len(interactions) == 0,
    }


def _get_detail(drug_name: str, country: str, db: Session) -> dict:
    q = db.query(Drug).filter(
        Drug.brand_name.ilike(f"%{drug_name}%") |
        Drug.brand_name_en.ilike(f"%{drug_name}%") |
        Drug.brand_name_zh.ilike(f"%{drug_name}%") |
        Drug.generic_name.ilike(f"%{drug_name}%")
    )
    if country != "any":
        c = Country.US if country == "US" else Country.CN
        q = q.filter(Drug.country == c)
    drug = q.first()
    if not drug:
        return {"error": f"Drug '{drug_name}' not found"}
    return _drug_detail(drug)


# ── Serializers ───────────────────────────────────────────────────────────────

def _drug_summary(d: Drug) -> dict:
    return {
        "id": d.id,
        "brand_name_en": d.brand_name_en,
        "brand_name_zh": d.brand_name_zh,
        "generic_name": d.generic_name,
        "generic_name_zh": d.generic_name_zh,
        "country": d.country.value,
        "prescription_status": d.prescription_status.value,
        "strength": d.strength,
        "atc_code": d.atc_code,
    }


def _drug_detail(d: Drug) -> dict:
    return {
        **_drug_summary(d),
        "manufacturer": d.manufacturer or d.manufacturer_zh,
        "indications": d.indications,
        "indications_zh": d.indications_zh,
        "dosage_form": d.dosage_form,
        "special_warnings": d.special_warnings,
        "special_warnings_zh": d.special_warnings_zh,
        "requires_refrigeration": d.requires_refrigeration,
        "is_injectable": d.is_injectable,
        "ingredients": [
            {"name_en": link.ingredient.name_en, "name_zh": link.ingredient.name_zh}
            for link in d.ingredients if link.ingredient
        ],
    }


# Avoid circular import
from app.models.drug import DrugIngredient
