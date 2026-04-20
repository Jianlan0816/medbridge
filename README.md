# 💊 MedBridge · 药桥

> **Find your medicine across borders — AI-powered US ↔ China drug translation and safety agent**
> 跨国找药，安全出行 — 中美药品智能翻译与安全检查

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)](https://fastapi.tiangolo.com)
[![Claude](https://img.shields.io/badge/Powered%20by-Claude%20AI-orange)](https://anthropic.com)
[![License](https://img.shields.io/badge/License-MIT-gray)](LICENSE)

---

## The Problem

You take Ozempic in the US. You're traveling to China for 3 months. What do you buy there?

- Drug brand names are completely different across countries
- Same ingredient, different dosage strengths
- Some US drugs aren't approved in China (and vice versa)
- Prescription rules differ — what's OTC in China may need Rx in the US
- Combining drugs from two countries can cause dangerous interactions

**MedBridge solves this.** Type in your drug name or condition → get safe, bilingual equivalents.

---

## Features

### 🔍 Mode 1: Search by Condition
Enter a medical condition (in English or Chinese) → get recommended drugs available in **both the US and China**, side by side.

```
Input:  "type 2 diabetes"
Output: Glucophage (US) ↔ 格华止 (CN) · Metformin 500mg · Rx both countries
        Ozempic (US) ↔ 诺和泰 (CN) · Semaglutide · ⚠️ Requires refrigeration
        Jardiance (US) ↔ 欧唐静 (CN) · Empagliflozin · Rx both countries
```

### 💊 Mode 2: Translate My Medicine
Enter your current drug brand → find the exact equivalent in the other country.

```
Input:  "Advil" (US → CN)
Output: 芬必得 (China) · Ibuprofen 300mg sustained-release · OTC ✅
        ⚠️ Different strength: US 200mg vs CN 300mg sustained-release
```

### 🔗 Drug-Drug Interaction Check
List all your medications → the agent checks every combination for dangerous interactions.

```
Input:  ["Xarelto", "Advil"]
Output: ⚠️ MAJOR — Rivaroxaban + Ibuprofen significantly increases bleeding risk
```

---

## How It Works (Agentic AI)

MedBridge uses **Claude AI with tool_use** — the agent plans its own research, calls multiple databases, and synthesizes a safety-aware bilingual response.

```
User Query
    ↓
Orchestrator Agent (Claude Opus)
    ├── search_drugs_by_condition()   → openFDA + seeded DB
    ├── search_drugs_by_brand()       → brand name lookup EN/ZH
    ├── find_equivalents()            → ATC code bridge US↔CN
    ├── check_interactions()          → DDI database
    └── get_drug_detail()             → full bilingual details
    ↓
Structured bilingual response (EN + ZH)
```

**The ATC Bridge:** Every drug worldwide maps to a WHO ATC code regardless of brand or language.
`Tylenol = 泰诺 = ATC:N02BE01 (paracetamol)` — this is how we match across countries.

---

## Project Structure

```
MedBridge/
├── backend/
│   ├── app/
│   │   ├── models/drug.py          # SQLAlchemy models: Drug, Ingredient, ATC, DDI
│   │   ├── pipeline/
│   │   │   ├── seed.py             # 28 curated US↔CN drug pairs (7 conditions)
│   │   │   ├── openfda.py          # Live FDA drug label ingestion
│   │   │   └── nmpa.py             # Chinese NMPA drug scraper
│   │   ├── tools/drug_tools.py     # 5 agent tools Claude can call
│   │   ├── agents/orchestrator.py  # Multi-step agentic reasoning loop
│   │   ├── database.py             # SQLAlchemy + SQLite setup
│   │   └── main.py                 # FastAPI endpoints
│   └── requirements.txt
├── frontend/
│   └── index.html                  # Bilingual single-page UI (no build step)
├── .env.example
└── README.md
```

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/Jianlan0816/medbridge.git
cd medbridge/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp ../.env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 3. Run the backend

```bash
uvicorn app.main:app --reload
# → http://localhost:8000
# → http://localhost:8000/docs  (interactive API explorer)
```

### 4. Open the frontend

Open `frontend/index.html` in your browser — no build step needed.

---

## API Reference

### `POST /api/search/condition`
Search drugs by medical condition.

```json
{
  "condition": "type 2 diabetes",
  "from_country": "US",
  "to_country": "CN"
}
```

### `POST /api/search/brand`
Translate a drug brand to another country + DDI check.

```json
{
  "brand_name": "Ozempic",
  "from_country": "US",
  "to_country": "CN",
  "other_drugs": ["Metformin", "Aspirin"]
}
```

### `GET /api/drugs/{id}`
Get full bilingual details for a drug by ID.

---

## Seeded Drug Coverage

| Condition | US Drug | CN Equivalent |
|---|---|---|
| Diabetes | Glucophage, Ozempic, Jardiance | 格华止, 诺和泰, 欧唐静 |
| Hypertension | Altace, Capoten, Concor | 瑞泰, 开博通, 康忻 |
| Pain / Fever | Tylenol, Advil | 泰诺, 百服宁, 芬必得 |
| Antibiotics | Amoxil | 阿莫西林胶囊 |
| Mental Health | Zoloft, Prozac | 左洛复, 百忧解 |
| Blood Thinner | Xarelto | 拜瑞妥 |
| Cholesterol | Lipitor | 立普妥 |
| Cancer | Keytruda | 可瑞达 |

---

## Data Sources

| Source | What it provides |
|---|---|
| [openFDA](https://open.fda.gov/apis/drug/label/) | FDA-approved drugs, labels, ingredients |
| [NMPA / 国家药监局](https://www.nmpa.gov.cn) | China-approved drugs |
| [WHO ATC](https://www.whocc.no/atc_ddd_index/) | Universal drug classification bridge |
| [DrugBank](https://drugbank.com) | Drug-drug interaction database |
| Curated seed data | 28 hand-verified US↔CN drug pairs |

---

## Roadmap

- [ ] Add Japan, EU country support
- [ ] Mobile app (React Native)
- [ ] Pharmacist-verified drug pairs
- [ ] Travel prescription letter generator (bilingual PDF)
- [ ] Integration with pharmacy APIs for real-time availability
- [ ] User accounts to save medication list

---

## ⚠️ Medical Disclaimer

MedBridge provides **information only** and is not a substitute for professional medical advice. Always consult a licensed pharmacist or physician before changing, substituting, or stopping any medication.

本工具**仅供参考**，不能替代专业医疗建议。更换、替代或停止任何药物前，请务必咨询执业药剂师或医生。

---

## Author

**Jianlan Ren** — Biochemistry (B.S.) · Bioinformatics (M.S.) · Computer Science (Ph.D.)

Built with ❤️ for the 5M+ people who travel between the US and China every year.

---

*Powered by [Claude AI](https://anthropic.com) · Built with [FastAPI](https://fastapi.tiangolo.com)*
