# Untagged Opportunities — Agentic Partner Retagging

> **Owner:** Riccardo Carlo Conte  
> **Status:** Phase 1 — In Development  
> **Repo:** `RCC-cap/untagged-opportunities`

## Problem Statement

In the THOR pipeline, **78,631 out of 202,396 opportunities have no partner tag**:

| Category | Count |
|----------|-------|
| "No Vendor/Partner" | 55,068 |
| "-" (dash / blank) | 23,563 |
| **Total Untagged** | **78,631** |

Currently, partner tagging is done manually via VBA macros in a 60MB `.xlsm` file. This project replaces that with an **autonomous AI agent** that:

1. Extracts the file from SharePoint automatically
2. Identifies untagged opportunities
3. Recommends the best-fit partner using AI
4. Sends approval requests to Sales Leads
5. Writes accepted tags back and maintains an audit log

---

## Architecture Overview

```
┌───────────────┐     ┌──────────────┐     ┌─────────────────────┐
│ 1. EXTRACT    │────▶│ 2. FILTER    │────▶│ 3. ANALYSIS ENGINE  │
│ SharePoint    │     │ Untagged     │     │ • Keyword matching   │
│ .xlsm → read  │     │ rows only    │     │ • Similarity scoring │
└───────────────┘     └──────────────┘     │ • Taxonomy rules     │
                                           │ • Hyperscaler boost  │
                                           │ → Confidence 0–100   │
                                           └──────────┬──────────┘
                                                      │
                      ┌──────────────┐     ┌──────────▼──────────┐
                      │ 6. FEEDBACK  │◀────│ 4. APPROVAL         │
                      │ Learning     │     │ Sales Lead reviews   │
                      │ loop         │     │ Accept / Reject /    │
                      └──────┬───────┘     │ Override             │
                             │             └─────────────────────┘
                      ┌──────▼───────┐     ┌─────────────────────┐
                      │ 7. UPDATE    │────▶│ 5. AUDIT LOG        │
                      │ Write tag    │     │ Full traceability    │
                      │ back         │     │                     │
                      └──────────────┘     └─────────────────────┘
```

---

## Data Source

| Property | Value |
|----------|-------|
| File | `VBA 1.xlsm` |
| Size | ~60 MB |
| Rows | 202,396 |
| Location | SharePoint (fixed path) |
| Format | `.xlsm` (Excel with VBA macros) |

### Key Columns (29)

| Column | Column | Column |
|--------|--------|--------|
| Opportunity Line ID | Opportunity ID | Account Name |
| Opportunity Name | Euro Bkngs | Weighted Euro Booking |
| Contribution | Stage | Contract Sign Date |
| Year | CM% | Offer |
| Portfolio | Selling SBU/BU/MU/MS | Country |
| **Partner** ← target | Technology | Opp Creation Date |
| Sales Stage Date | Delivery SBU/Unit | Business Line (L1-L3) |
| Sector | Primary GOU | Interco Flag |
| Probability% | Bid Type | Opp Type |
| Account Type | Opty Lead | |

### Current Partner Distribution

| Partner | Count |
|---------|-------|
| No Vendor/Partner | 55,068 |
| - (dash) | 23,563 |
| Microsoft | 30,000 |
| SAP | 14,000 |
| AWS | 10,000 |
| Oracle | 7,600 |
| Google | 5,200 |

---

## Phase 1 — XLS-Based Workflow (No THOR API)

### Pipeline Steps

| Step | Component | Description | Tech |
|------|-----------|-------------|------|
| 1 | **Trigger** | Scheduled daily at 10:00 AM | n8n Schedule Node |
| 2 | **Extract** | Fetch `.xlsm` from SharePoint via Microsoft Graph API | n8n HTTP Request / SharePoint Node |
| 3 | **Parse** | Stream-read XLS to handle 200k+ rows efficiently (chunked read, not full load) | Python `openpyxl` read-only mode / `polars` |
| 4 | **Filter** | Keep only untagged rows (`Partner` = empty / "-" / "No Vendor/Partner") + sold last month | Python / n8n Code Node |
| 5 | **Batch** | Split into batches of 50–100 rows per AI call | n8n SplitInBatches |
| 6 | **AI Recommend** | For each batch: keyword extraction, similarity scoring, taxonomy mapping, confidence score | Azure OpenAI (gpt-4o-mini) |
| 7 | **Generate Email** | Build HTML approval email with Accept / Reject / Override links | n8n Code Node |
| 8 | **Send** | Email to Sales Lead / Opportunity Owner | Outlook Node / Power Automate |
| 9 | **Capture Response** | Webhook receives Accept/Reject/Override + optional feedback | n8n Webhook |
| 10 | **Update Dataset** | Write partner tag back to results file on SharePoint | Microsoft Graph API |
| 11 | **Audit Log** | Append: OppID, recommendation, decision, rationale, timestamp | Azure Blob / SharePoint |

### Performance Strategy for 200k+ Rows

The `.xlsm` file is **60MB with 202,396 rows**. Key optimizations:

- **Streaming read**: Use `openpyxl` in `read_only=True` mode or `polars.read_excel()` — avoids loading entire file in memory
- **Column selection**: Read only the 29 relevant columns, skip VBA/macro sheets
- **Early filter**: Filter untagged rows immediately during read (don't store 200k rows, process ~78k)
- **Batch processing**: Process in chunks of 50–100 rows for AI calls
- **Delta processing**: Track already-processed Opportunity IDs to avoid re-processing
- **Incremental runs**: Daily runs only process new/changed untagged rows

### Analysis Engine Logic

```
For each untagged opportunity:
  1. KEYWORD MATCH    → Extract keywords from: Opp Name, Offer, Portfolio, Technology
  2. SIMILARITY SCORE → Compare against historically tagged opps (same sector/offer/tech)
  3. TAXONOMY RULES   → Map keywords → partner (e.g. "Azure" → Microsoft, "S/4HANA" → SAP)
  4. HYPERSCALER BOOST → Microsoft, AWS, Google, SAP, Oracle get priority weight
  5. CONFIDENCE CALC  → Combine scores → 0–100
  6. OUTPUT           → { primary_partner, secondary_partner, rationale, confidence }
```

### Configurable / Trainable Logic

- **Taxonomy rules** are stored in a config file (JSON/YAML) — editable without code changes
- **Hyperscaler priority weights** are configurable
- **Feedback loop**: Accepted/Rejected decisions are stored and fed back as few-shot examples
- **Override tracking**: When Sales Lead overrides a suggestion, the override is logged and used to improve future recommendations

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Orchestration | n8n (self-hosted) or Azure Logic Apps |
| AI Reasoning | Azure OpenAI — gpt-4o-mini (batch), gpt-4o (complex) |
| Data I/O | SharePoint via Microsoft Graph API |
| XLS Parsing | Python `openpyxl` (read-only) / `polars` |
| Approval Flow | Power Automate Approvals / Adaptive Cards (Teams) |
| Audit Storage | Azure Blob Storage / SharePoint List |
| Config | JSON taxonomy + YAML rules |

---

## Project Structure

```
untagged-opportunities/
├── README.md                  ← You are here
├── src/
│   ├── extract/               ← SharePoint file extraction
│   │   └── sharepoint_reader.py
│   ├── parse/                 ← XLS parsing (streaming, 200k rows)
│   │   └── xls_parser.py
│   ├── filter/                ← Untagged row identification
│   │   └── filter_untagged.py
│   ├── engine/                ← Analysis engine (keyword, similarity, taxonomy)
│   │   ├── keyword_extractor.py
│   │   ├── similarity_scorer.py
│   │   ├── taxonomy_mapper.py
│   │   └── recommender.py
│   ├── approval/              ← Email generation & response capture
│   │   ├── email_builder.py
│   │   └── webhook_handler.py
│   ├── update/                ← Write-back to SharePoint
│   │   └── dataset_updater.py
│   └── audit/                 ← Audit logging
│       └── audit_logger.py
├── config/
│   ├── taxonomy.json          ← Keyword → Partner mapping rules
│   ├── partners.yaml          ← Partner list + priority weights
│   └── settings.yaml          ← Schedule, batch size, thresholds
├── workflows/
│   └── n8n_workflow.json      ← Importable n8n workflow
├── tests/
│   └── ...
├── data/
│   └── .gitkeep               ← Local data (gitignored)
├── .env.example               ← Environment variables template
├── .gitignore
├── requirements.txt
└── pyproject.toml
```

---

## Future Phases

| Phase | Description |
|-------|-------------|
| **Phase 2** | Replace XLS with Salesforce API (read/write opportunities directly) |
| **Phase 3** | THOR-specific taxonomy integration + native THOR API |

---

## Getting Started

```bash
# Clone (use a path OUTSIDE OneDrive to avoid sync issues)
git clone https://github.com/RCC-cap/untagged-opportunities.git C:\Dev\untagged-opportunities
cd C:\Dev\untagged-opportunities

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy env template
copy .env.example .env
# Edit .env with your SharePoint credentials, Azure OpenAI key, etc.
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SHAREPOINT_SITE_URL` | SharePoint site URL |
| `SHAREPOINT_FILE_PATH` | Path to `.xlsm` file in SharePoint |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint |
| `AZURE_OPENAI_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | Deployment name (e.g. `gpt-4o-mini`) |
| `SMTP_HOST` | Email server for sending approvals |
| `WEBHOOK_BASE_URL` | Base URL for approval webhooks |
| `AUDIT_STORAGE_PATH` | Azure Blob / SharePoint path for audit logs |

---

## License

Internal — NTT DATA