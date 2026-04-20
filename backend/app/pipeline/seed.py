"""
Seed database with curated US↔CN drug pairs for the most common conditions.
This gives the app immediate value before live API calls are made.
Covers: diabetes, hypertension, pain, infection, mental health, cancer support.
"""

from sqlalchemy.orm import Session
from app.models.drug import (
    Drug, ActiveIngredient, DrugIngredient, ATCCode,
    Country, PrescriptionStatus, DDISeverity, DrugInteraction
)

# ── Seed data ─────────────────────────────────────────────────────────────────
# Format: (atc_code, name_en, name_zh, level descriptions)
ATC_CODES = [
    ("A10BA02", "Metformin", "二甲双胍", "A", "A10", "A10B", "A10BA"),
    ("A10BJ02", "Semaglutide", "司美格鲁肽", "A", "A10", "A10B", "A10BJ"),
    ("A10BK01", "Empagliflozin", "恩格列净", "A", "A10", "A10B", "A10BK"),
    ("C09AA05", "Ramipril", "雷米普利", "C", "C09", "C09A", "C09AA"),
    ("C09AA01", "Captopril", "卡托普利", "C", "C09", "C09A", "C09AA"),
    ("C07AB07", "Bisoprolol", "比索洛尔", "C", "C07", "C07A", "C07AB"),
    ("N02BE01", "Paracetamol", "对乙酰氨基酚", "N", "N02", "N02B", "N02BE"),
    ("M01AE01", "Ibuprofen", "布洛芬", "M", "M01", "M01A", "M01AE"),
    ("N02AA01", "Morphine", "吗啡", "N", "N02", "N02A", "N02AA"),
    ("J01CA04", "Amoxicillin", "阿莫西林", "J", "J01", "J01C", "J01CA"),
    ("N06AB06", "Sertraline", "舍曲林", "N", "N06", "N06A", "N06AB"),
    ("N06AB03", "Fluoxetine", "氟西汀", "N", "N06", "N06A", "N06AB"),
    ("L01XC32", "Pembrolizumab", "帕博利珠单抗", "L", "L01", "L01X", "L01XC"),
    ("B01AF01", "Rivaroxaban", "利伐沙班", "B", "B01", "B01A", "B01AF"),
    ("C10AA05", "Atorvastatin", "阿托伐他汀", "C", "C10", "C10A", "C10AA"),
]

# (brand_en, brand_zh, generic_en, generic_zh, atc, country, rx_status, indications_en, indications_zh, manufacturer, strength, warnings_en, warnings_zh)
DRUGS = [
    # ── Diabetes ────────────────────────────────────────────────────────────
    ("Glucophage", "格华止", "Metformin", "二甲双胍", "A10BA02", "US",
     "Rx", "Type 2 diabetes", "2型糖尿病", "Bristol-Myers Squibb", "500mg/850mg/1000mg tablet",
     None, None),
    ("Glucophage", "格华止", "Metformin", "二甲双胍", "A10BA02", "CN",
     "Rx", "Type 2 diabetes", "2型糖尿病", "默克雪兰诺", "500mg tablet",
     None, None),
    ("二甲双胍", "二甲双胍片", "Metformin", "二甲双胍", "A10BA02", "CN",
     "Rx", "Type 2 diabetes", "2型糖尿病", "多家国产厂商", "250mg/500mg tablet",
     None, None),
    ("Ozempic", "诺和泰", "Semaglutide", "司美格鲁肽", "A10BJ02", "US",
     "Rx", "Type 2 diabetes, weight management", "2型糖尿病，体重管理",
     "Novo Nordisk", "0.5mg/1mg/2mg weekly injection",
     "Requires refrigeration. Injectable.", "需冷藏保存。注射剂型。"),
    ("Ozempic", "诺和泰", "Semaglutide", "司美格鲁肽", "A10BJ02", "CN",
     "Rx", "Type 2 diabetes", "2型糖尿病",
     "诺和诺德（中国）", "0.5mg/1mg weekly injection",
     "需冷藏保存。注射剂型。", "需冷藏保存。注射剂型。"),
    ("Jardiance", "欧唐静", "Empagliflozin", "恩格列净", "A10BK01", "US",
     "Rx", "Type 2 diabetes, heart failure", "2型糖尿病，心力衰竭",
     "Boehringer Ingelheim", "10mg/25mg tablet", None, None),
    ("Jardiance", "欧唐静", "Empagliflozin", "恩格列净", "A10BK01", "CN",
     "Rx", "Type 2 diabetes", "2型糖尿病",
     "勃林格殷格翰", "10mg/25mg tablet", None, None),

    # ── Hypertension ────────────────────────────────────────────────────────
    ("Altace", "瑞泰", "Ramipril", "雷米普利", "C09AA05", "US",
     "Rx", "Hypertension, heart failure", "高血压，心力衰竭",
     "Pfizer", "2.5mg/5mg/10mg capsule", None, None),
    ("Capoten", "开博通", "Captopril", "卡托普利", "C09AA01", "US",
     "Rx", "Hypertension", "高血压", "Par Pharmaceutical", "25mg/50mg/100mg tablet", None, None),
    ("开博通", "开博通", "Captopril", "卡托普利", "C09AA01", "CN",
     "Rx", "Hypertension", "高血压", "施贵宝", "25mg tablet", None, None),
    ("Concor", "康忻", "Bisoprolol", "比索洛尔", "C07AB07", "US",
     "Rx", "Hypertension, angina", "高血压，心绞痛", "Merck", "5mg/10mg tablet", None, None),
    ("Concor", "康忻", "Bisoprolol", "比索洛尔", "C07AB07", "CN",
     "Rx", "Hypertension, angina", "高血压，心绞痛", "默克雪兰诺", "5mg tablet", None, None),

    # ── Pain / Fever ────────────────────────────────────────────────────────
    ("Tylenol", "泰诺", "Paracetamol", "对乙酰氨基酚", "N02BE01", "US",
     "OTC", "Pain, fever, headache", "疼痛，发烧，头痛",
     "Johnson & Johnson", "325mg/500mg/650mg tablet",
     "Do not exceed 4g/day. Avoid with alcohol.", "每日不超过4克。避免与酒精同用。"),
    ("泰诺", "泰诺", "Paracetamol", "对乙酰氨基酚", "N02BE01", "CN",
     "OTC", "Pain, fever, headache", "疼痛，发烧，头痛",
     "强生", "500mg tablet",
     "每日不超过4克。避免与酒精同用。", "每日不超过4克。避免与酒精同用。"),
    ("百服宁", "百服宁", "Paracetamol", "对乙酰氨基酚", "N02BE01", "CN",
     "OTC", "Pain, fever", "疼痛，发烧",
     "中美天津史克", "500mg tablet", None, None),
    ("Advil", "芬必得", "Ibuprofen", "布洛芬", "M01AE01", "US",
     "OTC", "Pain, fever, inflammation", "疼痛，发烧，炎症",
     "Pfizer", "200mg/400mg tablet",
     "Take with food. Avoid with blood thinners.", "随食物服用。避免与抗凝血药同用。"),
    ("芬必得", "芬必得", "Ibuprofen", "布洛芬", "M01AE01", "CN",
     "OTC", "Pain, fever, inflammation", "疼痛，发烧，炎症",
     "中美天津史克", "300mg sustained-release capsule",
     "随食物服用。", "随食物服用。"),

    # ── Antibiotics ─────────────────────────────────────────────────────────
    ("Amoxil", "阿莫仙", "Amoxicillin", "阿莫西林", "J01CA04", "US",
     "Rx", "Bacterial infections", "细菌感染", "GSK", "250mg/500mg capsule", None, None),
    ("阿莫西林", "阿莫西林胶囊", "Amoxicillin", "阿莫西林", "J01CA04", "CN",
     "Rx", "Bacterial infections", "细菌感染", "多家国产厂商", "250mg/500mg capsule", None, None),

    # ── Mental Health ────────────────────────────────────────────────────────
    ("Zoloft", "左洛复", "Sertraline", "舍曲林", "N06AB06", "US",
     "Rx", "Depression, anxiety, OCD", "抑郁症，焦虑症，强迫症",
     "Pfizer", "25mg/50mg/100mg tablet", None, None),
    ("左洛复", "左洛复", "Sertraline", "舍曲林", "N06AB06", "CN",
     "Rx", "Depression, anxiety", "抑郁症，焦虑症",
     "辉瑞", "50mg tablet", None, None),
    ("Prozac", "百忧解", "Fluoxetine", "氟西汀", "N06AB03", "US",
     "Rx", "Depression, OCD, bulimia", "抑郁症，强迫症，神经性贪食症",
     "Eli Lilly", "10mg/20mg/40mg capsule", None, None),
    ("百忧解", "百忧解", "Fluoxetine", "氟西汀", "N06AB03", "CN",
     "Rx", "Depression", "抑郁症", "礼来", "20mg capsule", None, None),

    # ── Blood Thinner ────────────────────────────────────────────────────────
    ("Xarelto", "拜瑞妥", "Rivaroxaban", "利伐沙班", "B01AF01", "US",
     "Rx", "Blood clot prevention, atrial fibrillation", "预防血栓，心房颤动",
     "Bayer/J&J", "10mg/15mg/20mg tablet",
     "Do NOT stop without doctor approval. Bleeding risk.", "未经医生批准切勿停药。出血风险。"),
    ("拜瑞妥", "拜瑞妥", "Rivaroxaban", "利伐沙班", "B01AF01", "CN",
     "Rx", "Blood clot prevention, atrial fibrillation", "预防血栓，心房颤动",
     "拜耳", "10mg/15mg/20mg tablet",
     "未经医生批准切勿停药。出血风险。", "未经医生批准切勿停药。出血风险。"),

    # ── Cholesterol ─────────────────────────────────────────────────────────
    ("Lipitor", "立普妥", "Atorvastatin", "阿托伐他汀", "C10AA05", "US",
     "Rx", "High cholesterol, heart disease prevention", "高胆固醇，预防心脏病",
     "Pfizer", "10mg/20mg/40mg/80mg tablet", None, None),
    ("立普妥", "立普妥", "Atorvastatin", "阿托伐他汀", "C10AA05", "CN",
     "Rx", "High cholesterol", "高胆固醇",
     "辉瑞", "10mg/20mg tablet", None, None),

    # ── Cancer ──────────────────────────────────────────────────────────────
    ("Keytruda", "可瑞达", "Pembrolizumab", "帕博利珠单抗", "L01XC32", "US",
     "Rx", "Multiple cancers (lung, breast, melanoma, etc.)", "多种癌症（肺癌、乳腺癌、黑色素瘤等）",
     "Merck", "100mg/4ml injection",
     "Requires IV infusion. Hospital administration only.", "需静脉输注。仅限医院使用。"),
    ("可瑞达", "可瑞达", "Pembrolizumab", "帕博利珠单抗", "L01XC32", "CN",
     "Rx", "Lung cancer, melanoma", "肺癌，黑色素瘤",
     "默沙东", "100mg/4ml injection",
     "需静脉输注。仅限医院使用。", "需静脉输注。仅限医院使用。"),
]

# Known DDIs: (ingredient_a_en, ingredient_b_en, severity, description_en, description_zh)
INTERACTIONS = [
    ("ibuprofen", "rivaroxaban", "major",
     "Combining ibuprofen with rivaroxaban significantly increases bleeding risk.",
     "布洛芬与利伐沙班合用显著增加出血风险。"),
    ("ibuprofen", "paracetamol", "minor",
     "Generally safe to combine at standard doses, but monitor for GI issues.",
     "标准剂量下通常可以合用，但需注意胃肠道反应。"),
    ("sertraline", "fluoxetine", "contraindicated",
     "Do not combine two SSRIs — risk of serotonin syndrome.",
     "禁止合用两种SSRI药物——有血清素综合征风险。"),
    ("metformin", "empagliflozin", "minor",
     "Often prescribed together safely for type 2 diabetes.",
     "两者通常可安全联用于2型糖尿病治疗。"),
    ("atorvastatin", "rivaroxaban", "moderate",
     "Some CYP3A4 interaction — monitor for muscle pain (myopathy).",
     "存在CYP3A4相互作用——注意肌肉疼痛（肌病）。"),
]


def run(db: Session) -> None:
    """Seed all ATC codes, drugs, and interactions."""
    print("Seeding ATC codes...")
    _seed_atc(db)

    print("Seeding drugs...")
    _seed_drugs(db)

    print("Seeding drug interactions...")
    _seed_interactions(db)

    db.commit()
    print("✅ Seed complete.")


def _seed_atc(db: Session) -> None:
    for code, name_en, name_zh, l1, l2, l3, l4 in ATC_CODES:
        if db.get(ATCCode, code):
            continue
        db.add(ATCCode(
            code=code, name_en=name_en, name_zh=name_zh,
            level1=l1, level2=l2, level3=l3, level4=l4,
        ))
    db.flush()


def _seed_drugs(db: Session) -> None:
    for (brand_en, brand_zh, generic_en, generic_zh, atc, country_str,
         rx, ind_en, ind_zh, mfr, strength, warn_en, warn_zh) in DRUGS:

        country = Country.US if country_str == "US" else Country.CN
        rx_status = {
            "OTC": PrescriptionStatus.otc,
            "Rx": PrescriptionStatus.prescription,
            "controlled": PrescriptionStatus.controlled,
        }.get(rx, PrescriptionStatus.unknown)

        existing = db.query(Drug).filter_by(
            brand_name=brand_zh if country == Country.CN else brand_en,
            country=country
        ).first()
        if existing:
            continue

        drug = Drug(
            country=country,
            brand_name=brand_zh if country == Country.CN else brand_en,
            brand_name_en=brand_en,
            brand_name_zh=brand_zh,
            generic_name=generic_en,
            generic_name_zh=generic_zh,
            atc_code=atc,
            prescription_status=rx_status,
            indications=ind_en,
            indications_zh=ind_zh,
            manufacturer=mfr if country == Country.US else None,
            manufacturer_zh=mfr if country == Country.CN else None,
            strength=strength,
            special_warnings=warn_en,
            special_warnings_zh=warn_zh,
            requires_refrigeration="冷藏" in (warn_zh or "") or "refrigeration" in (warn_en or "").lower(),
            is_injectable="injection" in (strength or "").lower() or "注射" in (strength or ""),
            source="seed",
        )
        db.add(drug)
        db.flush()

        # Link ingredient
        ing = db.query(ActiveIngredient).filter_by(name_en=generic_en.lower()).first()
        if not ing:
            ing = ActiveIngredient(name_en=generic_en.lower(), name_zh=generic_zh)
            db.add(ing)
            db.flush()
        elif not ing.name_zh and generic_zh:
            ing.name_zh = generic_zh

        db.add(DrugIngredient(drug_id=drug.id, ingredient_id=ing.id, is_primary=True))


def _seed_interactions(db: Session) -> None:
    severity_map = {
        "contraindicated": DDISeverity.contraindicated,
        "major": DDISeverity.major,
        "moderate": DDISeverity.moderate,
        "minor": DDISeverity.minor,
    }
    for ing_a, ing_b, severity_str, desc_en, desc_zh in INTERACTIONS:
        a = db.query(ActiveIngredient).filter_by(name_en=ing_a).first()
        b = db.query(ActiveIngredient).filter_by(name_en=ing_b).first()
        if not a or not b:
            continue
        existing = db.query(DrugInteraction).filter_by(
            ingredient_a_id=a.id, ingredient_b_id=b.id
        ).first()
        if existing:
            continue
        db.add(DrugInteraction(
            ingredient_a_id=a.id,
            ingredient_b_id=b.id,
            severity=severity_map[severity_str],
            description=desc_en,
            description_zh=desc_zh,
            source="seed",
        ))
