# THOR — Wireframe & User Flow Diagrams

**Version:** 1.1 — Updated 2026-05-07 (reflects deployed Phase 1 implementation)

## 1. System Architecture Flow (End-to-End)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        THOR AGENTIC PARTNER TAGGING — SYSTEM FLOW               │
└─────────────────────────────────────────────────────────────────────────────────┘

 ┌──────────┐    ┌──────────┐    ┌───────────────┐    ┌──────────────┐
 │  TRIGGER │───▶│  EXTRACT │───▶│    FILTER     │───▶│    BATCH     │
 │ POST     │    │ Azure    │    │ Untagged only │    │ 6 rows/call  │
 │ /api/run │    │ Blob     │    │ Skip processed│    │ (test mode)  │
 │ or Cron  │    │ .xlsx    │    │ via Cosmos DB │    └──────┬───────┘
 └──────────┘    └──────────┘    └───────────────┘           │
                                                             ▼
                                                 ┌───────────────────────┐
                                                 │   AI RECOMMENDATION   │
                                                 │                       │
                                                 │  1. Keyword Extract   │
                                                 │  2. Taxonomy Map      │
                                                 │  3. Similarity Score  │
                                                 │  4. Account History   │
                                                 │  5. LLM Reasoning     │
                                                 │  6. Confidence Calc   │
                                                 └───────────┬───────────┘
                                                             │
                                                  ┌──────────┴──────────┐
                                                  │  Match found?       │
                                                  └──────────┬──────────┘
                                                  YES        │         NO
                                          ┌──────────────────┴──────────────────┐
                                          ▼                                     ▼
                                  ┌──────────────┐                     ┌──────────────┐
                                  │  INTERNAL    │                     │ THOR AGENT   │
                                  │  MATCH       │                     │ WEB FALLBACK │
                                  │              │                     │              │
                                  │ Partner +    │                     │ Azure OpenAI │
                                  │ 50-100%      │                     │ researches   │
                                  │ confidence   │                     │ public info  │
                                  └──────┬───────┘                     │ → partner +  │
                                         │                             │ 15-45% conf  │
                                         │                             └──────┬───────┘
                                         │                                    │
                                         └──────────────┬─────────────────────┘
                                                        ▼
                                  ┌──────────────────────────────────────────┐
                                  │         BUILD DIGEST EMAIL               │
                                  │                                          │
                                  │  Group by Sales Lead → by Account Name   │
                                  │  Render cards: Internal / AI / No match  │
                                  │  Include confidence badge + rationale    │
                                  │  "View in browser" tip for Outlook       │
                                  └────────────────────┬─────────────────────┘
                                                       │
                                                       ▼
                                              ┌────────────────┐
                                              │  Power Automate│
                                              │  Webhook       │
                                              │  → Outlook     │
                                              └────────┬───────┘
                                                       │
                                                       ▼
                                              ┌────────────────┐
                                              │  SALES LEAD    │
                                              │  Opens Email   │
                                              │                │
                                              │ 3 card types:  │
                                              │ • Internal 🟢🟡│
                                              │ • AI Sugg. 🟠  │
                                              │ • No match 🔴  │
                                              └──┬─────┬────┬──┘
                                                 │     │    │
                                   ┌─────────────┘     │    └──────────────┐
                                   ▼                   ▼                   ▼
                           ┌────────────┐      ┌────────────┐      ┌────────────┐
                           │   ACCEPT   │      │  SUGGEST   │      │    SKIP    │
                           │            │      │  DIFFERENT │      │  (Reject)  │
                           │ Write tag  │      │            │      │            │
                           │ to Cosmos  │      │ Web form → │      │ Flag for   │
                           │ + Blob     │      │ user types │      │ manual     │
                           └──────┬─────┘      │ partner +  │      └─────┬──────┘
                                  │            │ rationale  │            │
                                  │            └──────┬─────┘            │
                                  │                   │                  │
                                  └───────────────────┼──────────────────┘
                                                      ▼
                                  ┌─────────────────────────────────────────────┐
                                  │           PERSISTENCE LAYER                  │
                                  │                                             │
                                  │  ┌─────────┐  ┌──────────┐  ┌───────────┐  │
                                  │  │Cosmos DB │  │ Blob     │  │ JSONL     │  │
                                  │  │pipeline- │  │decisions/│  │ audit log │  │
                                  │  │state     │  │          │  │           │  │
                                  │  └─────────┘  └──────────┘  └───────────┘  │
                                  └─────────────────────────────────────────────┘
```

---

## 2. User Journey Map (Sales Lead Perspective)

```
 ──────────────────────────────────────────────────────────────────────────────
  TIME ──────────────────────────────────────────────────────────────────────▶

  ┌─────────┐     ┌─────────────┐     ┌───────────┐     ┌──────────────────┐
  │  10:00  │     │  ~10:15 AM  │     │  When     │     │    Immediate     │
  │  AM     │     │  (depends   │     │  Sales    │     │    (after        │
  │         │     │  on batch)  │     │  Lead     │     │     click)       │
  │ Agent   │────▶│ Email lands │────▶│ reads &   │────▶│  Confirmation    │
  │ runs    │     │ in inbox    │     │ decides   │     │  shown           │
  └─────────┘     └─────────────┘     └───────────┘     └──────────────────┘
       │                 │                   │                     │
       │                 │                   │                     │
  [No user         [User sees         [User picks         [Tag applied
   action]          notification]      a partner]           or flagged]
```

---

## 3. Email Wireframe — Digest Email (Implemented)

### 3.1 Digest Email — One per Sales Lead, Grouped by Account

```
┌─────────────────────────────────────────────────────────────────┐
│ From: Power Automate (thor-agent@company.com)                   │
│ To: mario.rossi@company.com                                     │
│ Subject: THOR — 6 Partner Tag Recommendations for Review        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  THOR                          Partner Tag Recommendations      │
│  ────────────────────────────────────────────────────────────   │
│                                                                 │
│  💡 For best viewing experience, open this email in             │
│     your browser.                                               │
│                                                                 │
│  Hi Mario,                                                      │
│                                                                 │
│  6 opportunities in your pipeline need a partner tag.           │
│  Below are AI-generated recommendations based on account        │
│  history, technology signals, and taxonomy matching.             │
│                                                                 │
│  🟢 80%+ High   🟡 50-79% Medium   🔴 <50% Low                │
│                                                                 │
│  ══════════════════════════════════════════════════════════════  │
│  ROCHE HOLDING AG                                               │
│  ══════════════════════════════════════════════════════════════  │
│                                                                 │
│  ┌──── CARD TYPE 1: INTERNAL MATCH ───────────────────────┐    │
│  │▌                                                       │    │
│  │▌ Cloud Transformation — Roche           Stage   [95%]  │    │
│  │▌                                                       │    │
│  │▌  Microsoft                                            │    │
│  │▌  Why: this account was previously tagged with         │    │
│  │▌  Microsoft (account override — 95% confidence).       │    │
│  │▌                                                       │    │
│  │▌  [Accept]  [Suggest different]  Skip                  │    │
│  │▌                                                       │    │
│  │▌  €1,200,000 booking value                             │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ══════════════════════════════════════════════════════════════  │
│  GSK | BE                                                       │
│  ══════════════════════════════════════════════════════════════  │
│                                                                 │
│  ┌──── CARD TYPE 2: THOR AGENT SUGGESTION ────────────────┐    │
│  │▌                                                       │    │
│  │▌ Digital Workplace Modernization       Stage [AI 35%]  │    │
│  │▌                                                       │    │
│  │▌  Microsoft        THOR AGENT SUGGESTION               │    │
│  │▌  No specific match found in internal data — THOR      │    │
│  │▌  Agent suggests an alternative based on public info:  │    │
│  │▌  GSK has a known multi-year partnership with          │    │
│  │▌  Microsoft for cloud and digital workplace            │    │
│  │▌  transformation across its global operations.         │    │
│  │▌                                                       │    │
│  │▌  [Accept Microsoft]  [Suggest different]  Skip        │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌──── CARD TYPE 3: NO MATCH ─────────────────────────────┐    │
│  │▌                                                       │    │
│  │▌ Procurement Services — GSK           Stage [No match] │    │
│  │▌                                                       │    │
│  │▌  No confident partner match found. Please suggest     │    │
│  │▌  the correct partner below.                           │    │
│  │▌                                                       │    │
│  │▌  [Suggest a partner]  Skip                            │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ──    │
│  THOR Partner Tagging · Capgemini Sales Operations              │
│                                          2026-05-07 10:15 UTC   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Card Types — Visual Guide

| Card Type | Left Border | Badge | Condition |
|-----------|-------------|-------|-----------|
| **Internal Match** | Green (#1e7e34) | `95%` green badge | Keyword/taxonomy/history match found |
| **THOR Agent Suggestion** | Amber (#b8860b) | `AI 35%` amber badge | No internal match; LLM identified likely partner from public info |
| **No Match** | Red (#c62828) | `No match` red badge | Neither internal nor LLM could identify a partner |

### 3.3 Suggest Partner Form (Web Page)

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ╔═══════════════════════════════════════════════════════════╗   │
│  ║  📝 Suggest a Different Partner                          ║   │
│  ║  None of THOR's recommendations fit? Tell us the correct ║   │
│  ║  partner.                                                ║   │
│  ╚═══════════════════════════════════════════════════════════╝   │
│                                                                 │
│   Opportunity: OPP-2026-045821                                  │
│                                                                 │
│   Partner Name                                                  │
│   ┌──────────────────────────────────────────────────────┐     │
│   │ e.g. Microsoft, AWS, SAP, ServiceNow...              │     │
│   └──────────────────────────────────────────────────────┘     │
│   Type the partner that should be tagged for this opportunity.  │
│                                                                 │
│   ┌──────────────────────────────────────────────────────┐     │
│   │          ✓ Submit Suggestion                         │     │
│   └──────────────────────────────────────────────────────┘     │
│                                                                 │
│  ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ──    │
│  Your suggestion will be recorded and the partner tag applied   │
│  to this opportunity. THOR learns from your feedback.           │
└─────────────────────────────────────────────────────────────────┘
```

### 3.4 Confirmation Pages

**After Accept:**
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                    ✅ Tag Applied Successfully                   │
│                                                                 │
│  Partner tag "Microsoft" has been applied to opportunity         │
│  OPP-2026-045821.                                               │
│                                                                 │
│  You may close this window.                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**After Skip (Reject):**
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                    ❌ All Recommendations Rejected               │
│                                                                 │
│  No partner has been applied to OPP-2026-045821.                │
│  This opportunity has been flagged for manual review             │
│  by Sales Operations.                                           │
│                                                                 │
│  You may close this window.                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**After Already Responded (idempotent):**
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                    ℹ️ Already Responded                          │
│                                                                 │
│  This opportunity was previously tagged as "Microsoft".         │
│  No further action needed.                                      │
│                                                                 │
│  You may close this window.                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Data Flow Diagram

```
┌───────────────┐         ┌───────────────┐         ┌───────────────┐
│  SharePoint   │         │  Azure Blob   │         │  Azure Key    │
│  Online       │         │  Storage      │         │  Vault        │
│               │         │               │         │               │
│  VBA 1.xlsm  │         │  audit/*.jsonl │         │  API keys     │
│  (202K rows)  │         │  results/     │         │  SP creds     │
└───────┬───────┘         └───────▲───────┘         └───────┬───────┘
        │                         │                         │
        │ Read                    │ Write                   │ Read
        ▼                         │                         ▼
┌───────────────────────────────────────────────────────────────────┐
│                        PYTHON APPLICATION                         │
│                                                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │
│  │  extract/  │  │  filter/   │  │  engine/   │  │  approval/ │  │
│  │            │  │            │  │            │  │            │  │
│  │ sharepoint │─▶│ filter_    │─▶│ keyword_   │─▶│ email_     │  │
│  │ _reader    │  │ untagged   │  │ extractor  │  │ builder    │  │
│  └────────────┘  └────────────┘  │ recommender│  │ webhook_   │  │
│                                  │ similarity │  │ handler    │  │
│                                  │ taxonomy_  │  └────────────┘  │
│                                  │ mapper     │                   │
│                                  └────────────┘                   │
│                                                                   │
│  ┌────────────┐  ┌────────────┐                                   │
│  │  update/   │  │  audit/    │                                   │
│  │            │  │            │                                   │
│  │ dataset_   │  │ audit_     │                                   │
│  │ updater    │  │ logger     │                                   │
│  └────────────┘  └────────────┘                                   │
└───────────────────────────────────────────────────────────────────┘
        │                                           │
        │ Trigger/Schedule                          │ Send
        ▼                                           ▼
┌───────────────┐                          ┌───────────────┐
│  n8n          │                          │  Microsoft    │
│  Workflow     │                          │  Graph API    │
│               │                          │  (Outlook)    │
│  Schedule     │                          │               │
│  10:00 daily  │                          │  → Sales Lead │
└───────────────┘                          └───────────────┘
```

---

## 5. Recommendation Engine — Decision Flow

```
                          ┌─────────────────────┐
                          │  UNTAGGED OPP ROW   │
                          │                     │
                          │  Opp Name, Offer,   │
                          │  Technology, Account │
                          └──────────┬──────────┘
                                     │
                                     ▼
                          ┌─────────────────────┐
                          │  KEYWORD EXTRACTION  │
                          │                     │
                          │  Extract meaningful │
                          │  terms from Opp Name│
                          │  + Offer + Tech     │
                          └──────────┬──────────┘
                                     │
                                     ▼
                          ┌─────────────────────┐
                          │  TAXONOMY MAPPING    │
                          │                     │
                          │  Match keywords to  │
                          │  partner rules in   │
                          │  taxonomy.json      │
                          └──────────┬──────────┘
                                     │
                                     ▼
                          ┌─────────────────────┐
                          │  SIMILARITY SCORING  │
                          │                     │
                          │  TF-IDF cosine sim  │
                          │  against historical │
                          │  tagged opps        │
                          └──────────┬──────────┘
                                     │
                                     ▼
                          ┌─────────────────────┐
                          │  ACCOUNT HISTORY     │
                          │                     │
                          │  Look up all prior  │
                          │  tagged deals for   │
                          │  same Account Name  │
                          │  → If 10 MSFT deals │
                          │    boost MSFT 1.5x  │
                          │  (strongest signal) │
                          └──────────┬──────────┘
                                     │
                                     ▼
                          ┌─────────────────────┐
                          │  WEIGHT APPLICATION  │
                          │                     │
                          │  Apply tier weights: │
                          │  T1: 1.1–1.3x       │
                          │  T2: 1.0x           │
                          │  T3: 0.9x           │
                          └──────────┬──────────┘
                                     │
                                     ▼
                          ┌─────────────────────┐
                          │  CONFIDENCE CALC     │
                          │                     │
                          │  Combine scores →   │
                          │  0–100 confidence   │
                          └──────────┬──────────┘
                                     │
                          ┌──────────┴──────────┐
                          │                     │
                          ▼                     ▼
                  ┌──────────────┐     ┌──────────────┐
                  │  CONF < 90%  │     │  CONF ≥ 90%  │
                  │              │     │              │
                  │ SEND EMAIL   │     │ AUTO-TAG     │
                  │ with score & │     │ + notify     │
                  │ rationale    │     │ (should-have)│
                  │              │     │              │
                  │ 🟢 80-100    │     └──────────────┘
                  │ 🟡 50-79     │
                  │ 🔴 0-49      │
                  └──────────────┘
```

---

## 6. Webhook Interaction Sequence

```
  Sales Lead                  Webhook Server              Dataset        Audit Log
      │                            │                        │               │
      │  Click [Accept]            │                        │               │
      │───────────────────────────▶│                        │               │
      │  GET /approve?opp_id=X     │                        │               │
      │       &partner=Microsoft   │                        │               │
      │       &token=<hmac_sig>    │                        │               │
      │                            │                        │               │
      │                            │── Validate token ──┐   │               │
      │                            │◀─────────────────────┘   │               │
      │                            │                        │               │
      │                            │── Write partner tag ──▶│               │
      │                            │                        │               │
      │                            │── Log decision ────────────────────────▶│
      │                            │                        │               │
      │◀───── HTML confirmation ───│                        │               │
      │  "Tag applied successfully"│                        │               │
      │                            │                        │               │
```

---

## 7. State Diagram — Opportunity Lifecycle

```
                    ┌─────────────────┐
                    │                 │
                    │    UNTAGGED     │ ◀── Initial state in source file
                    │                 │
                    └────────┬────────┘
                             │
                             │ Agent processes (ALL opps, any confidence)
                             ▼
              ┌──────────────────────────────┐
              │                              │
              │    RECOMMENDATION GENERATED  │
              │                              │
              │    3 possible outcomes:      │
              │    • Internal match (50-100%)│
              │    • THOR Agent sugg (15-45%)│
              │    • No match (0%)          │
              │                              │
              └──────────────┬───────────────┘
                             │
                             │ Digest email sent to Sales Lead
                             │ (grouped by account, with confidence badges)
                             ▼
                    ┌──────────────────┐
                    │                  │
                    │  PENDING_REVIEW  │ ── Email in Sales Lead's inbox
                    │                  │
                    └──┬─────┬─────┬──┘
                       │     │     │
            Accept     │     │     │  Skip
                       │     │     │
                       ▼     │     ▼
              ┌──────────┐   │   ┌────────────┐
              │          │   │   │            │
              │  TAGGED  │   │   │  REJECTED  │
              │          │   │   │  (flagged) │
              └──────────┘   │   └────────────┘
                             │
                    Suggest   │
                   different  │
                             ▼
                    ┌──────────────────┐
                    │                  │
                    │  SUGGESTED       │ ── Sales Lead typed
                    │  (user-tagged)   │    a different partner
                    │                  │
                    └──────────────────┘
                                    │
                                    │ Manual review
                                    ▼
                           ┌────────────────┐
                           │                │
                           │ MANUALLY_TAGGED│
                           │ or CONFIRMED   │
                           │ NO_PARTNER     │
                           └────────────────┘
```

---

## 8. Batch Processing Flow

```
 INITIAL RUN — Full Backlog: 78,631 opportunities
 ─────────────────────────────────────────────────────────────

 Hour 1:  [████████████████████░░░░░░░░░░░░░░░░░░░░]  ~25,000 processed
 Hour 2:  [████████████████████████████████████████░]  ~50,000 processed
 Hour 3:  [████████████████████████████████████████]   78,631 processed ✓

 SUBSEQUENT DAILY RUNS — Only new/unprocessed opportunities
 ─────────────────────────────────────────────────────────────

 Day 2:   [██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]  ~200 new opps → minutes
 Day 3:   [██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]  ~150 new opps → minutes

 Per Batch:
 ┌──────────────────────────────────────────────────────────────┐
 │  500 batches × 200 rows = 100,000 rows/day capacity          │
 │                                                              │
 │  Each batch:                                                 │
 │  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ... ┌─────┐                   │
 │  │ R1 │ │ R2 │ │ R3 │ │ R4 │     │R200 │ → 1 AI call        │
 │  └────┘ └────┘ └────┘ └────┘     └─────┘   (GPT 5.4)       │
 │         ↓                                                    │
 │  200 recommendations generated                               │
 │  Emails sent for those with conf ≥ 60%                       │
 └──────────────────────────────────────────────────────────────┘

 Skip Logic (already-processed):
 ┌──────────────────────────────────────────────────────────────┐
 │  On each run:                                                │
 │  1. Load audit log → set of already-processed OppIDs         │
 │  2. Filter source file → exclude processed OppIDs            │
 │  3. Only analyse NEW or CHANGED opportunities                │
 │  → Day 2+ runs take minutes, not hours                       │
 └──────────────────────────────────────────────────────────────┘
```

---

## 9. Component Responsibility Map

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              src/ modules                                │
├─────────────────┬───────────────────────────────────────────────────────┤
│  Module         │  Responsibility                                       │
├─────────────────┼───────────────────────────────────────────────────────┤
│  api.py         │  FastAPI app: /health, /api/run, /api/select,        │
│                 │  /api/reject, /api/suggest (GET+POST)                 │
│  main.py        │  Pipeline orchestrator: extract→filter→recommend→    │
│                 │  web_fallback→email→persist                           │
├─────────────────┼───────────────────────────────────────────────────────┤
│  extract/       │  blob_reader: download .xlsx from Azure Blob         │
│                 │  blob_writer: persist decisions + audit to Blob       │
│  parse/         │  xls_parser: read .xlsx with Polars/calamine         │
│  filter/        │  Select untagged rows, exclude already-processed      │
│  engine/        │  Core AI logic:                                       │
│                 │  · keyword_extractor: extract meaningful terms        │
│                 │  · taxonomy_mapper: match keywords to partner rules   │
│                 │  · similarity_scorer: TF-IDF cosine similarity        │
│                 │  · account_history: prior tagged deals scoring        │
│                 │  · llm_reasoner: Azure OpenAI reasoning               │
│                 │  · recommender: orchestrate signals → candidates      │
│                 │  · web_fallback: LLM research for no-match cases     │
│  approval/      │  email_builder: Jinja2 digest/single email HTML      │
│                 │  token_utils: HMAC-SHA256 token generation/verify     │
│                 │  webhook_handler: process Accept/Reject/Suggest       │
│  store/         │  state_manager: Cosmos DB state (processed, responses)│
│  update/        │  dataset_updater: write-back to source (future)       │
│  audit/         │  audit_logger: append-only JSONL audit trail          │
├─────────────────┼───────────────────────────────────────────────────────┤
│  config/        │  settings.yaml, partners.yaml, taxonomy.json          │
│  workflows/     │  n8n workflow definition (schedule + HTTP trigger)     │
│  tests/         │  Unit + integration tests                             │
└─────────────────┴───────────────────────────────────────────────────────┘
```

---

## 10. Mobile Email Rendering (Responsive)

```
┌──────────────────────────┐
│  THOR — Partner Tag      │
│  Recommendation          │
├──────────────────────────┤
│                          │
│  Opportunity:            │
│  OPP-2026-045821         │
│                          │
│  Cloud Migration —       │
│  Contoso AG              │
│                          │
│  Account: Contoso AG     │
│                          │
│  ── Partner Options ──   │
│                          │
│  #1 Microsoft   🟢 82%   │
│  "azure migration",      │
│  "fabric"; 10 prior      │
│  deals on account        │
│  ┌──────────────────┐    │
│  │ ✅ SELECT MSFT   │    │
│  └──────────────────┘    │
│                          │
│  #2 AWS         🟡 54%   │
│  "cloud migration"       │
│  (generic); 2 prior      │
│  deals on account        │
│  ┌──────────────────┐    │
│  │ ✅ SELECT AWS    │    │
│  └──────────────────┘    │
│                          │
│  #3 Google      🔴 21%   │
│  "cloud" only — weak     │
│  signal; no history      │
│  ┌──────────────────┐    │
│  │ ✅ SELECT GOOGLE │    │
│  └──────────────────┘    │
│                          │
│  ┌──────────────────┐    │
│  │ ❌ REJECT ALL    │    │
│  └──────────────────┘    │
│                          │
│  ── ── ── ── ── ── ──   │
│  Automated by THOR       │
└──────────────────────────┘
```
