# THOR — Wireframe & User Flow Diagrams

## 1. System Architecture Flow (End-to-End)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        THOR AGENTIC PARTNER TAGGING — SYSTEM FLOW               │
└─────────────────────────────────────────────────────────────────────────────────┘

 ┌──────────┐    ┌──────────┐    ┌───────────────┐    ┌──────────────┐
 │  TRIGGER │───▶│  EXTRACT │───▶│    FILTER     │───▶│    BATCH     │
 │ Cron 10AM│    │SharePoint│    │ Untagged only │    │ 50 rows/call │
 └──────────┘    │ .xlsm    │    │ Skip processed│    └──────┬───────┘
                 └──────────┘    └───────────────┘           │
                                                             ▼
                                                 ┌───────────────────────┐
                                                 │   AI RECOMMENDATION   │
                                                 │                       │
                                                 │  1. Keyword Extract   │
                                                 │  2. Taxonomy Map      │
                                                 │  3. Similarity Score  │
                                                 │  4. Partner Match     │
                                                 │  5. Confidence Calc   │
                                                 └───────────┬───────────┘
                                                             │
                                          ┌──────────────────┴──────────────────┐
                                          │                                     │
                                          ▼                                     ▼
                                  ┌──────────────┐                     ┌──────────────┐
                                  │  ALL opps    │     │  CONF ≥ 90%  │
                                  │  (any conf.) │     │  (future)    │
                                  │              │     │              │
                                  │ Send Email   │     │ Auto-Approve │
                                  │ to Sales Lead│     │ (write tag)  │
                                  │ with score + │     │              │
                                  │ rationale    │     │              │
                                  └──────┬───────┘     └──────┬───────┘
                                         │                    │
                                         ▼                    │
                                ┌────────────────┐            │
                                │  SALES LEAD    │            │
                                │  Opens Email   │            │
                                │                │            │
                                │ 🟢/🟡/🔴 conf │            │
                                │ + rationale    │            │
                                │                │            │
                                │ ┌────┐ ┌────┐  │            │
                                │ │ ✅ │ │ ❌ │  │            │
                                │ └──┬─┘ └──┬─┘  │            │
                                └────┼──────┼────┘            │
                                     │      │                 │
                        ┌────────────┘      └────────┐        │
                        ▼                            ▼        │
                ┌──────────────┐            ┌────────────┐    │
                │   ACCEPT     │            │   REJECT   │    │
                │              │            │            │    │
                │ Write tag    │            │ Flag for   │    │
                │ to dataset   │◀───────────│ manual     │    │
                └──────┬───────┘     │      └─────┬──────┘    │
                       │             │            │           │
                       ▼             │            ▼           ▼
                                  ┌─────────────────────────────────────────────┐
                                  │              AUDIT LOG (JSONL)               │
                                  │                                             │
                                  │  {opp_id, partner, decision, confidence,    │
                                  │   rationale, reviewer, timestamp, method}   │
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

## 3. Email Wireframe (Low-Fidelity)

### 3.1 Recommendation Email — Multi-Partner Choice

```
┌─────────────────────────────────────────────────────────────────┐
│ From: thor-agent@company.com                                    │
│ To: mario.rossi@company.com                                     │
│ Subject: THOR — Partner Tag Recommendation for Review           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ╔═══════════════════════════════════════════════════════════╗   │
│  ║  THOR — Partner Tag Recommendation            [LOGO]     ║   │
│  ╚═══════════════════════════════════════════════════════════╝   │
│                                                                 │
│  The following opportunity needs a partner tag:                  │
│                                                                 │
│  ┌─────────────────────┬──────────────────────────────────┐     │
│  │ Opportunity ID      │ OPP-2026-045821                  │     │
│  │ Opportunity Name    │ Cloud Migration — Contoso AG     │     │
│  │ Account             │ Contoso AG                       │     │
│  │ Technology          │ Cloud Infrastructure             │     │
│  │ Offer               │ Azure Migration                  │     │
│  └─────────────────────┴──────────────────────────────────┘     │
│                                                                 │
│  Based on keyword analysis, account history, and taxonomy       │
│  mapping, here are the recommended partners:                    │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  #1  MICROSOFT                              🟢 82%       │   │
│  │                                                          │   │
│  │  Keywords: "azure migration", "fabric"                   │   │
│  │  Offer match: Azure Migration (exact)                    │   │
│  │  Account history: 10 prior Microsoft deals               │   │
│  │                                                          │   │
│  │  ┌──────────────────────────┐                            │   │
│  │  │  ✅ SELECT MICROSOFT     │                            │   │
│  │  └──────────────────────────┘                            │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │  #2  AWS                                    🟡 54%       │   │
│  │                                                          │   │
│  │  Keywords: "cloud migration" (generic)                   │   │
│  │  Account history: 2 prior AWS deals                      │   │
│  │                                                          │   │
│  │  ┌──────────────────────────┐                            │   │
│  │  │  ✅ SELECT AWS            │                            │   │
│  │  └──────────────────────────┘                            │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │  #3  GOOGLE                                 🔴 21%       │   │
│  │                                                          │   │
│  │  Keywords: "cloud" only — weak/generic signal            │   │
│  │  No account history                                      │   │
│  │                                                          │   │
│  │  ┌──────────────────────────┐                            │   │
│  │  │  ✅ SELECT GOOGLE         │                            │   │
│  │  └──────────────────────────┘                            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  None of these?                                                 │
│  ┌──────────────────────────┐                                   │
│  │  ❌ REJECT ALL            │                                   │
│  └──────────────────────────┘                                   │
│                                                                 │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─    │
│  This is an automated recommendation from the THOR Agentic     │
│  Partner Tagging system. Do not reply to this email.            │
│  Recommendation ID: REC-2026-045821-001                         │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Confirmation Page (After Partner Selection)

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                    ✅ Tag Applied Successfully                   │
│                                                                 │
│  Partner tag "Microsoft" has been applied to:                   │
│                                                                 │
│  • Opportunity: OPP-2026-045821                                 │
│  • Account: Contoso AG                                          │
│  • Recorded at: 2026-05-03 14:32:01 UTC                         │
│                                                                 │
│  You may close this window.                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Confirmation Page (After Reject All)

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                    ❌ All Recommendations Rejected               │
│                                                                 │
│  No partner has been applied to OPP-2026-045821.                │
│  This opportunity has been flagged for manual review             │
│  by Sales Operations.                                           │
│                                                                 │
│  Recorded at: 2026-05-03 14:32:01 UTC                           │
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
              │    (confidence 0–100)        │
              │                              │
              └──────────────┬───────────────┘
                             │
                             │ Email ALWAYS sent to Sales Lead
                             │ (with 🟢/🟡/🔴 label + rationale)
                             ▼
                    ┌──────────────────┐
                    │                  │
                    │  PENDING_REVIEW  │ ── Email in Sales Lead's inbox
                    │                  │
                    └────┬────────┬────┘
                         │        │
              Accept     │        │  Reject
                         ▼        ▼
              ┌────────────┐  ┌────────────┐
              │            │  │            │
              │   TAGGED   │  │  REJECTED  │
              │            │  │  (flagged) │
              └────────────┘  └────────────┘
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
├────────────────┬────────────────────────────────────────────────────────┤
│  Module        │  Responsibility                                        │
├────────────────┼────────────────────────────────────────────────────────┤
│  extract/      │  Connect to SharePoint, download .xlsm, parse to DF   │
│  parse/        │  Read .xlsm sheets, handle VBA macros, normalize cols  │
│  filter/       │  Select untagged rows, exclude already-processed       │
│  engine/       │  Core AI logic: keywords, taxonomy, similarity, score  │
│  approval/     │  Build HTML emails, handle webhook Accept/Reject       │
│  update/       │  Write partner tag back to dataset                     │
│  audit/        │  Append JSONL audit records for every action           │
├────────────────┼────────────────────────────────────────────────────────┤
│  config/       │  YAML settings, partner weights, JSON taxonomy rules   │
│  workflows/    │  n8n workflow definition (schedule + orchestration)     │
│  tests/        │  Unit + integration tests                              │
└────────────────┴────────────────────────────────────────────────────────┘
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
