# Coding Agent Session — MedBridge
**Agent:** Claude (Anthropic)  
**Date:** April 2025  
**Duration:** Single session (~4 hours)  
**GitHub:** https://github.com/Jianlan0816/medbridge  

---

## What I Built

MedBridge is an AI-powered bilingual drug translation platform that helps patients find safe medication equivalents when traveling between the US and China. The agent built the entire product from scratch in one session.

---

## What I Asked the Agent to Do

I described the product idea in plain English:

> "I want a tool where someone can type 'Ozempic' and instantly find its Chinese equivalent '诺和泰' — with dosage comparison, drug interaction checks, prescription status, and safety warnings. And a second mode where someone searches by condition and gets recommended drugs in both countries."

The agent took that and executed end-to-end.

---

## What the Agent Built

### Backend (Python / FastAPI)

**`backend/app/models/drug.py`**  
SQLAlchemy ORM models for the entire data layer:
- `Drug` — branded/generic products in US or CN, with bilingual fields
- `ActiveIngredient` — normalized ingredient bridge across brand names
- `ATCCode` — WHO Anatomical Therapeutic Chemical codes (universal drug ID)
- `DrugIngredient` — M2M table with dosage info
- `DrugInteraction` — DDI pairs with severity levels (contraindicated/major/moderate/minor)
- `FamilyLink` — caregiver monitoring (senior → family member alerts)
- `SearchLog` — anonymized query logging for analytics

**`backend/app/pipeline/seed.py`**  
Curated seed database of 28 verified US↔CN drug pairs across 8 conditions:
- Diabetes: Glucophage↔格华止, Ozempic↔诺和泰, Jardiance↔欧唐静
- Hypertension: Concor↔康忻, Capoten↔开博通
- Pain/Fever: Tylenol↔泰诺, Advil↔芬必得
- Mental Health: Zoloft↔左洛复, Prozac↔百忧解
- Blood Thinners: Xarelto↔拜瑞妥
- Cholesterol: Lipitor↔立普妥
- Cancer: Keytruda↔可瑞达
- Antibiotics: Amoxil↔阿莫西林

**`backend/app/pipeline/openfda.py`**  
Live FDA drug label ingestion via openFDA REST API:
- Async HTTP with retry logic (tenacity)
- Parses brand names, generic names, indications, prescription status, active ingredients
- Upserts into SQLite/PostgreSQL via SQLAlchemy

**`backend/app/pipeline/nmpa.py`**  
Chinese NMPA drug database scraper:
- Scrapes ouryao.com (public NMPA mirror) via BeautifulSoup
- Handles Chinese character encoding
- Falls back to local DB on network failure

**`backend/app/tools/drug_tools.py`**  
Five agent tools Claude calls during reasoning:
```
search_drugs_by_condition(condition, country)
search_drugs_by_brand(name, country)
find_equivalents(drug_name, from_country, to_country)
check_interactions(drug_names[])
get_drug_detail(drug_name, country)
```
Each tool queries the database and returns structured JSON the orchestrator uses to reason.

**`backend/app/agents/orchestrator.py`**  
Multi-step agentic reasoning loop using Claude's tool_use API:
```python
# Simplified flow:
messages = [{"role": "user", "content": user_query}]
while True:
    response = claude.messages.create(tools=TOOLS, messages=messages)
    if response.stop_reason == "end_turn":
        return extract_final_response(response)
    if response.stop_reason == "tool_use":
        results = [execute_tool(block) for block in response.content]
        messages.append(tool_results)
```
The agent plans its own research strategy — decides which databases to query, in what order, and when it has enough information to synthesize a response. Max 8 iterations.

**`backend/app/main.py`**  
FastAPI application with two endpoints:
- `POST /api/search/condition` — Mode 1: condition → drug recommendations
- `POST /api/search/brand` — Mode 2: brand name → cross-country equivalent + DDI
- `GET /api/drugs/{id}` — full drug detail

Auto-seeds database on startup. CORS configured for web + mobile clients.

---

### Frontend (Vanilla HTML + Tailwind)

**`frontend/demo.html`**  
Fully interactive single-page demo — no build step, no backend required.

**Three modes:**

**Mode 1 — Search by Condition**  
Enter any medical condition in English or Chinese → get drug recommendations for US and China side by side, with WHO ATC codes, dosage info, manufacturer, and bilingual instructions.

**Mode 2 — Translate My Drug**  
Enter a brand name (English or Chinese) → find the exact equivalent in the other country, with dosage comparison, match quality badge (exact/generic/similar), DDI check, and safety flags.

**Mode 3 — Access Abroad** *(new)*  
For drugs unavailable in your home country — find where to get them legally:
- Medical tourism destinations ranked by cost + accessibility
- International telehealth providers
- Active clinical trials (free access)
- Approved biosimilars
- Legal warnings (e.g., Adderall is criminal in China/Japan even with US prescription)

Demo includes animated agent "thinking" steps showing real tool calls being made, progress bar, and structured bilingual results.

---

### Sales Package

The agent also generated the full B2B go-to-market package:

**`sales/pitch.html`** — Print-to-PDF one-pager with:
- Problem stats ($300B medication non-adherence, 5M+ US-China travelers)
- How it works (4-step flow with real example)
- Pilot offer ($2,000/month, 60 days, 1,000 users)
- Product roadmap (3 modes, mobile app, API)
- Founder credentials

**`sales/outreach.md`** — 3-email cold outreach sequence:
- Email 1: The hook (problem statement)
- Email 2: The proof (specific examples for their company)
- Email 3: The close (pilot offer with deadline)
- LinkedIn message variant
- Objection handling scripts for 5 common responses

**`sales/targets.md`** — 30+ prioritized B2B targets across:
- Travel insurance (Allianz, AXA, Seven Corners, IMG Global)
- Corporate HR (Mercer, Aon, CIGNA Global, International SOS)
- Pharmacy chains (CVS, Walgreens, 99 Ranch)
- Hospital systems (Apollo, UCSF, Johns Hopkins International)

---

## Git History (single session)

```
9153416  Add B2B sales package: pitch one-pager, cold email sequence, target list
5bc8acd  Add Mode 3: Access Abroad — global drug access intelligence  
172a17d  Add interactive HTML demo with mock agent responses
b365db2  Add README with project overview, quickstart, and API docs
1362df3  Initial commit: MedBridge — bilingual drug translation & safety agent
```

All commits in one session. All pushed to GitHub.

---

## What I Directed vs What the Agent Did

| My decisions | Agent's execution |
|---|---|
| Product concept and 3-mode structure | All file creation and code writing |
| Data model requirements | SQLAlchemy schema design |
| Which conditions/drugs to seed | Full seed.py with 28 drug pairs + DDI data |
| "Use Claude tool_use for the agent loop" | Orchestrator implementation with retry logic |
| UI feel and bilingual requirement | 1,200-line demo.html with animations |
| B2B sales strategy | Full pitch, email sequence, target list |
| Git commit messages | Git init, staging, committing, pushing |

---

## Key Technical Decisions the Agent Made Independently

1. **ATC code as the bridge** — used WHO Anatomical Therapeutic Chemical codes to match drugs across countries without relying on name matching (which fails across languages)
2. **Seed-first strategy** — built a curated seed database rather than relying entirely on live API calls, so the app works immediately without rate limits
3. **Fallback chain** — openFDA → NMPA scraper → local DB, with graceful degradation at each step
4. **Tool result accumulation** — structured the agentic loop so each tool result is appended to message history, giving Claude full context for reasoning
5. **Severity-aware DDI rendering** — color-coded interaction warnings (contraindicated → red, major → orange, moderate → yellow, minor → green) in the UI

---

## Live Links

- **GitHub:** https://github.com/Jianlan0816/medbridge
- **Demo:** Open `frontend/demo.html` in any browser (no server needed)
- **API docs:** Run backend → visit `localhost:8000/docs`

---

## Stack

```
Backend:    Python 3.11 · FastAPI · SQLAlchemy · Claude API (tool_use)
Scraping:   httpx · BeautifulSoup · tenacity (retry)
Database:   SQLite (dev) · PostgreSQL-ready
Frontend:   Vanilla HTML · Tailwind CSS · Vanilla JS
AI:         Anthropic Claude claude-opus-4-5 (orchestrator)
DevOps:     Git · GitHub · dotenv
```
