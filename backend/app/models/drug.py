"""
Core data models for MedBridge.

Drug               — a single branded/generic product in one country
ActiveIngredient   — normalized ingredient (e.g. ibuprofen, 二甲双胍)
DrugIngredient     — M2M: drug ↔ ingredient with dosage
ATCCode            — WHO ATC classification (universal bridge between countries)
DrugInteraction    — known DDI pairs with severity
SearchLog          — anonymized query log for improving recommendations
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean,
    DateTime, ForeignKey, Text, Enum
)
from sqlalchemy.orm import relationship, DeclarativeBase
import enum


class Base(DeclarativeBase):
    pass


class Country(str, enum.Enum):
    US = "US"
    CN = "CN"


class PrescriptionStatus(str, enum.Enum):
    otc = "OTC"               # over the counter
    prescription = "Rx"       # prescription required
    controlled = "controlled" # controlled substance
    unknown = "unknown"


class DDISeverity(str, enum.Enum):
    contraindicated = "contraindicated"   # never combine
    major = "major"                       # avoid, serious risk
    moderate = "moderate"                 # use with caution
    minor = "minor"                       # minimal risk


class Drug(Base):
    """A branded or generic drug product in a specific country."""
    __tablename__ = "drugs"

    id = Column(Integer, primary_key=True)
    country = Column(Enum(Country), nullable=False, index=True)

    # Names
    brand_name = Column(String, nullable=False, index=True)       # "Advil", "芬必得"
    brand_name_en = Column(String, nullable=True)                  # English name always
    brand_name_zh = Column(String, nullable=True)                  # Chinese name always
    generic_name = Column(String, nullable=True)                   # "ibuprofen"
    generic_name_zh = Column(String, nullable=True)                # "布洛芬"

    # Manufacturer
    manufacturer = Column(String, nullable=True)
    manufacturer_zh = Column(String, nullable=True)

    # Classification
    atc_code = Column(String, ForeignKey("atc_codes.code"), nullable=True, index=True)
    prescription_status = Column(Enum(PrescriptionStatus), default=PrescriptionStatus.unknown)

    # Indications (what it treats)
    indications = Column(Text, nullable=True)            # comma-separated EN
    indications_zh = Column(Text, nullable=True)         # comma-separated ZH

    # Form & dosage
    dosage_form = Column(String, nullable=True)          # "tablet", "capsule", "injection"
    strength = Column(String, nullable=True)             # "200mg", "500mg/5ml"

    # Safety flags
    requires_refrigeration = Column(Boolean, default=False)
    is_injectable = Column(Boolean, default=False)
    special_warnings = Column(Text, nullable=True)
    special_warnings_zh = Column(Text, nullable=True)

    # Source metadata
    source = Column(String, nullable=True)               # "openFDA", "NMPA", "manual"
    source_id = Column(String, nullable=True)            # original ID in source system
    last_updated = Column(DateTime, default=datetime.utcnow)

    # Relationships
    atc = relationship("ATCCode", back_populates="drugs")
    ingredients = relationship("DrugIngredient", back_populates="drug")


class ActiveIngredient(Base):
    """Normalized active ingredient — the universal bridge across brands."""
    __tablename__ = "active_ingredients"

    id = Column(Integer, primary_key=True)
    name_en = Column(String, unique=True, nullable=False, index=True)  # "ibuprofen"
    name_zh = Column(String, nullable=True, index=True)                # "布洛芬"
    rxcui = Column(String, nullable=True)     # RxNorm concept ID
    drugbank_id = Column(String, nullable=True)

    drug_links = relationship("DrugIngredient", back_populates="ingredient")
    interactions_as_a = relationship("DrugInteraction", foreign_keys="DrugInteraction.ingredient_a_id", back_populates="ingredient_a")
    interactions_as_b = relationship("DrugInteraction", foreign_keys="DrugInteraction.ingredient_b_id", back_populates="ingredient_b")


class DrugIngredient(Base):
    """Many-to-many: Drug ↔ ActiveIngredient with dosage info."""
    __tablename__ = "drug_ingredients"

    id = Column(Integer, primary_key=True)
    drug_id = Column(Integer, ForeignKey("drugs.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("active_ingredients.id"), nullable=False)
    strength_mg = Column(Float, nullable=True)         # numeric mg amount
    strength_unit = Column(String, nullable=True)      # "mg", "mcg", "mg/ml"
    is_primary = Column(Boolean, default=True)         # primary vs inactive ingredient

    drug = relationship("Drug", back_populates="ingredients")
    ingredient = relationship("ActiveIngredient", back_populates="drug_links")


class ATCCode(Base):
    """
    WHO Anatomical Therapeutic Chemical classification.
    This is the universal bridge between US and Chinese drugs.
    e.g. N02BE01 = paracetamol = Tylenol = 泰诺 = acetaminophen
    """
    __tablename__ = "atc_codes"

    code = Column(String, primary_key=True)     # "N02BE01"
    level1 = Column(String, nullable=True)       # "N" = Nervous system
    level2 = Column(String, nullable=True)       # "N02" = Analgesics
    level3 = Column(String, nullable=True)       # "N02B" = Other analgesics
    level4 = Column(String, nullable=True)       # "N02BE" = Anilides
    name_en = Column(String, nullable=True)      # "Paracetamol"
    name_zh = Column(String, nullable=True)      # "对乙酰氨基酚"

    drugs = relationship("Drug", back_populates="atc")


class DrugInteraction(Base):
    """Known drug-drug interactions between active ingredients."""
    __tablename__ = "drug_interactions"

    id = Column(Integer, primary_key=True)
    ingredient_a_id = Column(Integer, ForeignKey("active_ingredients.id"), nullable=False)
    ingredient_b_id = Column(Integer, ForeignKey("active_ingredients.id"), nullable=False)
    severity = Column(Enum(DDISeverity), nullable=False)
    description = Column(Text, nullable=True)
    description_zh = Column(Text, nullable=True)
    mechanism = Column(Text, nullable=True)
    source = Column(String, nullable=True)   # "DrugBank", "FDA", "literature"

    ingredient_a = relationship("ActiveIngredient", foreign_keys=[ingredient_a_id], back_populates="interactions_as_a")
    ingredient_b = relationship("ActiveIngredient", foreign_keys=[ingredient_b_id], back_populates="interactions_as_b")


class SearchLog(Base):
    """Anonymized search log — powers analytics and improves suggestions."""
    __tablename__ = "search_logs"

    id = Column(Integer, primary_key=True)
    mode = Column(String, nullable=False)        # "condition" | "brand"
    query = Column(String, nullable=False)
    from_country = Column(String, nullable=True)
    to_country = Column(String, nullable=True)
    result_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
