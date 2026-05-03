# Product Requirements Document (PRD)

## THOR — Agentic Partner Tagging for Untagged Opportunities

| Field | Value |
|-------|-------|
| **Owner** | Riccardo Carlo Conte |
| **Version** | 1.0 |
| **Date** | 2026-05-03 |
| **Status** | Phase 1 — In Development |
| **Repo** | `RCC-cap/Untagged-Opportunities` |

---

## 1. Product Summary

THOR Agentic Partner Tagging is a **backend-only autonomous agent** that analyses 78,631 untagged opportunities in the THOR pipeline and recommends the best-fit technology partner for each. The agent runs daily, applies AI-based keyword matching, similarity scoring, and taxonomy rules, then sends a **one-click approval email** to the responsible Sales Lead. The user never interacts with a UI beyond the email. Accepted tags are written back to the source dataset and a full audit trail is maintained.

**Main Goal:** Eliminate manual partner tagging (currently done via VBA macros in a 60 MB `.xlsm` file) and replace it with an intelligent, auditable, feedback-driven automation.

---

## 2. Target Audience

| Persona | Role | Interaction |
|---------|------|-------------|
| **Sales Lead / Opportunity Owner** | Reviews AI recommendations | Receives email → clicks Accept / Reject |
| **Sales Operations** | Monitors tagging coverage & quality | Reviews audit logs and dashboards |
| **Data & Analytics Team** | Consumes clean, tagged data | No direct interaction with the agent |
| **System Admin** | Maintains infra & config | Manages n8n workflows, Azure resources, partner taxonomy |

---

## 3. Core Features

### 3.1 Must-Have (MVP — Phase 1)

| # | Feature | Description |
|---|---------|-------------|
| F1 | **Scheduled Extraction** | Daily at 10:00 AM, fetch `VBA 1.xlsm` from SharePoint / Azure Blob and parse all rows |
| F2 | **Filter Untagged** | Identify rows where Partner = "No Vendor/Partner", "-", or blank; skip already-processed |
| F3 | **AI Recommendation Engine** | Per opportunity: keyword extraction → taxonomy mapping → similarity scoring → generate **ranked list of candidate partners** each with individual confidence score (0–100) and rationale |
| F4 | **Hyperscaler Priority Weighting** | Tier-1 partners (Microsoft, SAP, AWS, Oracle, Google) receive configurable priority boost in scoring |
| F5 | **Multi-Partner Choice Email** | HTML email to Sales Lead showing opportunity details + **ranked partner list** with per-partner confidence score and rationale. Sales Lead clicks the partner they want to assign (one-click selection) or Reject All |
| F6 | **Webhook Response Capture** | Backend endpoints that record which partner was selected (or rejection), link it to OppID, and trigger downstream update |
| F7 | **Dataset Update** | Write accepted partner tag back to the results dataset (XLS / SharePoint list) |
| F8 | **Audit Logging** | Append-only JSONL log: OppID, recommendation, decision, timestamp, rationale, confidence, reviewer |
| F9 | **Batch Processing** | Process opportunities in configurable batches (default 200 rows/call); full backlog target: 1 day |
| F10 | **Always Send — Confidence Transparency** | Every untagged opportunity is sent to the Sales Lead regardless of confidence. The email clearly shows the confidence score and rationale so the human can make an informed decision |
| F11 | **Account History Scoring** | Look up all prior tagged deals for the same Account Name; if N deals share a partner tag, boost that partner's score proportionally (strongest signal for repeat clients) |
| F12 | **Skip Already-Processed** | Track processed OppIDs in audit log; on each run only scan new/unprocessed opportunities — never re-send for already-treated rows |

### Confidence Scoring Methodology

The confidence score (0–100) is computed as a **weighted sum of correlated signals**:

| Signal | Weight | Description | Example |
|--------|--------|-------------|--------|
| **Keyword Match** | 30% | Number and specificity of taxonomy keywords found in Opportunity Name + Offer + Technology fields. More keywords from the same partner = higher score. | "azure migration fabric" → 3 Microsoft keywords → high |
| **Keyword Correlation** | 20% | How strongly the found keywords correlate to a single partner vs. being generic. If all keywords point to the same partner → high; if keywords split across partners → low | "cloud infrastructure" is generic (low), "S/4HANA ABAP fiori" all point to SAP (high) |
| **Account History** | 30% | Ratio of prior tagged deals for the recommended partner on this account. If 10/12 prior deals = Microsoft → very high signal | Contoso AG: 10 MSFT deals → 30% × (10/12) = 25 pts |
| **Offer/Technology Exact Match** | 15% | Direct match between Offer or Technology field and a partner's known offerings in taxonomy.json | Offer = "Azure Migration" → exact Microsoft match |
| **Tier Weight Boost** | 5% | Tier-1 hyperscalers get a small bonus reflecting strategic priority | Microsoft tier 1 → +5 pts max |

**Formula:**
```
confidence = (keyword_score × 0.30)
           + (correlation_score × 0.20)
           + (account_history_score × 0.30)
           + (offer_match_score × 0.15)
           + (tier_boost × 0.05)
```

**Interpretation for Sales Lead:**
| Range | Label in Email | Meaning |
|-------|---------------|--------|
| 80–100 | 🟢 High Confidence | Multiple strong, correlated signals — very likely correct |
| 50–79 | 🟡 Medium Confidence | Some signals found but not all converge — review recommended |
| 0–49 | 🔴 Low Confidence | Weak or conflicting signals — best guess, needs human judgment |

### 3.2 Should-Have (Post-MVP Enhancements)

| # | Feature | Description |
|---|---------|-------------|
| S1 | **Auto-Approve** | If top partner confidence ≥ 90%, tag is written directly without human review |
| S2 | **Reminder Email** | If no response after 3 days, resend; escalate after 7 days |
| S3 | **Free-Text Override** | Sales Lead can type in a partner name not in the list via a form link |
| S4 | **Feedback Loop** | Selected/rejected decisions feed back into scoring weights to improve future accuracy |
| S5 | **Daily Summary Report** | Morning digest email to Sales Ops: X tagged, Y pending, Z rejected |

### 3.3 Could-Have (Future Phases)

| # | Feature | Description |
|---|---------|-------------|
| C1 | **Salesforce API Integration** | Read/write tags directly in CRM (Phase 2) |
| C2 | **THOR Taxonomy Sync** | Pull official taxonomy from THOR API for real-time rule updates (Phase 3) |
| C3 | **Web Dashboard** | Admin panel for taxonomy edits, score tuning, audit review |
| C4 | **Multi-Language Support** | Handle opportunity names in French, German, Italian, Spanish |
| C5 | **Slack/Teams Approval** | Adaptive Card or Slack block as alternative to email |

---

## 4. User Interface — Email Approval (Only UI Surface)

Since the system is entirely backend-driven, the **only user-facing interface** is the approval email.

### 4.1 Email Layout

```
┌────────────────────────────────────────────────────────────────┐
│  THOR — Partner Tag Recommendation                    [Logo]   │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  The following opportunity needs a partner tag:                 │
│                                                                │
│  ┌──────────────────────┬───────────────────────────────────┐  │
│  │ Opportunity ID       │ OPP-2026-045821                   │  │
│  │ Opportunity Name     │ Cloud Migration — Contoso AG      │  │
│  │ Account              │ Contoso AG                        │  │
│  │ Technology           │ Cloud Infrastructure              │  │
│  │ Offer                │ Azure Migration                   │  │
│  └──────────────────────┴───────────────────────────────────┘  │
│                                                                │
│  Based on keyword analysis, account history, and taxonomy       │
│  mapping, here are the recommended partners:                   │
│                                                                │
│  ┌─────┬──────────────┬─────────────┬─────────────────────┐    │
│  │  #  │ Partner      │ Confidence  │ Rationale           │    │
│  ├─────┼──────────────┼─────────────┼─────────────────────┤    │
│  │  1  │ Microsoft    │ 🟢 82%      │ Keywords: "azure    │    │
│  │     │              │             │ migration",         │    │
│  │     │              │             │ "fabric"; Offer     │    │
│  │     │              │             │ match; 10 prior     │    │
│  │     │              │             │ MSFT deals on acct  │    │
│  │     │ [ ✅ SELECT MICROSOFT ]    │                     │    │
│  ├─────┼──────────────┼─────────────┼─────────────────────┤    │
│  │  2  │ AWS          │ 🟡 54%      │ Keywords: "cloud    │    │
│  │     │              │             │ migration"; generic │    │
│  │     │              │             │ infra terms; 2 AWS  │    │
│  │     │              │             │ deals on account    │    │
│  │     │ [ ✅ SELECT AWS ]          │                     │    │
│  ├─────┼──────────────┼─────────────┼─────────────────────┤    │
│  │  3  │ Google       │ 🔴 21%      │ Keywords: "cloud"   │    │
│  │     │              │             │ only; no account    │    │
│  │     │              │             │ history             │    │
│  │     │ [ ✅ SELECT GOOGLE ]       │                     │    │
│  └─────┴──────────────┴─────────────┴─────────────────────┘    │
│                                                                │
│  None of these?                                                │
│  [ ❌ REJECT ALL ]                                             │
│                                                                │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─   │
│  This is an automated recommendation from the THOR Agentic    │
│  Partner Tagging system.                                       │
└────────────────────────────────────────────────────────────────┘
```

### 4.2 Button Behavior

| Button | Action | Result |
|--------|--------|--------|
| **Select [Partner]** | `GET /select?opp_id=X&partner=Y&token=Z` | Tag Y written to dataset, audit logged, confirmation shown |
| **Reject All** | `GET /reject?opp_id=X&token=Z` | OppID flagged as rejected, audit logged, no tag written |

Each partner row has its own Select button. The Sales Lead picks the one they agree with.

### 4.3 Confirmation Page (after click)

Simple HTML page served by the webhook:
- **Select:** "Thank you. Partner tag **[Partner Name]** has been applied to opportunity **[OPP-ID]**."
- **Reject All:** "Noted. This opportunity will remain untagged and has been flagged for manual review."

---

## 5. Navigation / User Flow

There is no multi-screen application. The user flow is linear and email-driven:

1. **Receive email** → User opens inbox
2. **Review partner options** → See ranked list with per-partner confidence + rationale
3. **Click Select on chosen partner** (or Reject All) → Single click, opens confirmation in browser
4. **Done** → No further action required

---

## 6. Sample Data

### 6.1 Example Opportunity (Input)

| Column | Value |
|--------|-------|
| Opportunity Line ID | OL-2026-112934 |
| Opportunity ID | OPP-2026-045821 |
| Account Name | Contoso AG |
| Opportunity Name | Cloud Migration — Contoso AG |
| Euro Bkngs | €1,200,000 |
| Stage | Proposal |
| Partner | No Vendor/Partner |
| Technology | Cloud Infrastructure |
| Offer | Azure Migration |
| Portfolio | Cloud & Infrastructure |
| Country | Germany |
| Opty Lead | mario.rossi@company.com |

### 6.2 Example Recommendation (Output)

```json
{
  "opp_id": "OPP-2026-045821",
  "candidates": [
    {
      "partner": "Microsoft",
      "confidence": 82,
      "rationale": "Keywords 'azure migration' and 'fabric' strongly match Microsoft taxonomy. Offer 'Azure Migration' is Microsoft-specific. Account Contoso AG has 10 prior Microsoft-tagged deals.",
      "signals": {"keyword_match": 28, "correlation": 18, "account_history": 25, "offer_match": 15, "tier_boost": 5}
    },
    {
      "partner": "AWS",
      "confidence": 54,
      "rationale": "Keywords 'cloud migration' and 'cloud infrastructure' are generic but partially match AWS taxonomy. Account has 2 prior AWS deals.",
      "signals": {"keyword_match": 18, "correlation": 10, "account_history": 12, "offer_match": 5, "tier_boost": 5}
    },
    {
      "partner": "Google",
      "confidence": 21,
      "rationale": "Only generic keyword 'cloud' matched. No account history with Google.",
      "signals": {"keyword_match": 8, "correlation": 4, "account_history": 0, "offer_match": 0, "tier_boost": 5}
    }
  ],
  "method": "keyword_match + correlation + taxonomy_rule + account_history + tier_boost"
}
```

---

## 7. Technical Requirements

### 7.1 Tech Stack

| Component | Technology |
|-----------|-----------|
| **Orchestration** | n8n (self-hosted) or Azure Logic Apps |
| **AI Model** | Azure OpenAI — `gpt-5.4` (batch + complex; large context window handles 200 rows/call) |
| **Language** | Python 3.11+ |
| **Data Source** | SharePoint Online / Azure Blob Storage (.xlsm) |
| **Email** | Microsoft Graph API / Outlook SMTP |
| **Webhooks** | Python (FastAPI or Flask) deployed on Azure App Service / Functions |
| **Audit Storage** | Azure Blob (JSONL files) or Azure Table Storage |
| **Scheduling** | n8n Schedule node (cron: `0 10 * * *`) |
| **Config** | YAML (partners, settings) + JSON (taxonomy rules) |

### 7.2 Key Libraries

| Library | Purpose |
|---------|---------|
| `openpyxl` | Parse .xlsm files |
| `pandas` | DataFrame processing |
| `openai` | Azure OpenAI SDK |
| `jinja2` | Email HTML templating |
| `pyyaml` | Config parsing |
| `fastapi` / `flask` | Webhook endpoints |
| `scikit-learn` | TF-IDF similarity scoring |

### 7.3 Infrastructure

- **Compute:** Azure Functions (consumption plan) or Azure App Service (B1)
- **Storage:** Azure Blob Storage (source files + audit logs)
- **Secrets:** Azure Key Vault (API keys, SharePoint credentials)
- **Monitoring:** Azure Application Insights + n8n execution logs

---

## 8. Styling & Design

| Aspect | Specification |
|--------|--------------|
| Email style | Corporate, clean, Segoe UI font |
| Colors | Primary: `#0078d4` (Microsoft Blue), Accept: `#107c10`, Reject: `#d83b01` |
| Layout | Single-column, max-width 700px, mobile-responsive |
| Confirmation page | Minimal white page, centered text, no navigation |
| Branding | "THOR" header, no heavy graphics (email client compatibility) |

---

## 9. Use Cases / User Flows

### UC-1: Happy Path — Accept Recommendation

1. Agent runs at 10:00 AM, processes full backlog in 200-row batches
2. For OPP-2026-045821: confidence = 82%, recommends Microsoft (account history: 10 prior Microsoft deals)
3. Email sent to mario.rossi@company.com
4. Mario opens email, reviews details, clicks **Accept**
5. Webhook fires → tag "Microsoft" written to dataset
6. Audit log entry created
7. Mario sees confirmation: "Partner tag Microsoft applied"

### UC-2: Reject Recommendation

1. Agent recommends "SAP" for an opportunity with confidence 64%
2. Sales Lead disagrees — clicks **Reject**
3. Opportunity stays untagged, flagged for manual review
4. Audit log records rejection

### UC-3: Low Confidence — Email Still Sent

1. Agent analyses opportunity, finds weak signals — confidence = 35%
2. Email still sent to Sales Lead with 🔴 Low Confidence label
3. Rationale explains: "Only 1 generic keyword matched; no account history available"
4. Sales Lead can Accept (if they know the context) or Reject
5. Every opp gets a chance — nothing is silently skipped

### UC-4: Auto-Approve (Should-Have)

1. Agent scores opportunity at 95% confidence (≥ 90% threshold)
2. Tag written directly without email
3. Audit log records "auto_approved"
4. Sales Lead receives informational notification (not approval)

### UC-5: No Response — Escalation (Should-Have)

1. Email sent, no click after 3 days → reminder sent
2. Still no response after 7 days → escalate to Sales Ops manager
3. Audit log records "escalated"

---

## 10. Out of Scope (Phase 1)

| Item | Reason |
|------|--------|
| Web dashboard / admin UI | Agent is headless; config via YAML/JSON files |
| Salesforce / CRM integration | Phase 2 scope |
| THOR API direct integration | Phase 3 scope |
| User authentication / login | No UI; webhook uses signed tokens |
| Payment or billing | Not applicable |
| Real-time processing | Daily batch is sufficient |
| Multi-file support | Single .xlsm source in Phase 1 |
| Partner override via email reply | Should-have for later |
| Mobile app | Email is mobile-friendly by design |
| ML model training | Uses rule-based + LLM; no custom model training |

---

## 11. Coding Standards

### 11.1 Code Style

- **Language:** Python 3.11+, type hints mandatory
- **Formatter:** `black` (line length 100)
- **Linter:** `ruff`
- **Naming:** `snake_case` for functions/variables, `PascalCase` for classes
- **Docstrings:** Google style, required for all public functions
- **Imports:** `isort` with black-compatible profile

### 11.2 Security

- All webhook URLs include HMAC-signed tokens (prevent unauthorized clicks)
- API keys stored in Azure Key Vault, never in code or config files
- Input validation on all webhook query parameters (OppID format, partner name allowlist)
- No PII in logs beyond email addresses (which are business contacts)
- HTTPS-only for all webhook endpoints

### 11.3 Testing

- **Unit tests:** `pytest`, minimum 80% coverage on engine modules
- **Integration tests:** Mock SharePoint + Azure OpenAI responses
- **Test data:** Synthetic opportunities (never production data in repo)
- **CI:** GitHub Actions — lint + test on every PR

### 11.4 Performance

- Batch processing: 200 rows per AI call, max 500 batches/day (100,000 rows/day)
- Target: Full 78K backlog processed in **< 1 day** (initial run); daily runs only process new/unprocessed opps
- Subsequent daily runs: Only new opportunities since last run (typically hundreds, not thousands)
- API rate limiting: Exponential backoff on 429 responses
- File parsing: Stream large .xlsm (don't load full file in memory)

### 11.5 Accessibility

- Email follows HTML email best practices (alt text, semantic tables)
- Buttons have sufficient contrast ratio (WCAG AA)
- Confirmation page is screen-reader friendly

---

## 12. Metrics & Success Criteria

| Metric | Target |
|--------|--------|
| Tagging coverage | Reduce untagged from 78,631 to < 5,000 within **2 days** of initial run |
| Acceptance rate | > 70% of recommendations accepted |
| Confidence accuracy | > 85% of accepted tags remain unchanged after 90 days |
| Processing speed | Full 78K backlog in < 1 day; daily delta (new opps) in < 1 hour |
| Response time | Average response within 48 hours of email sent |

---

## Appendix: Data Schema

### Key Columns in Source File

| Column | Type | Used For |
|--------|------|----------|
| Opportunity Line ID | String | Unique row identifier |
| Opportunity ID | String | Opportunity grouping |
| Account Name | String | Account history lookup |
| Opportunity Name | String | Keyword extraction (primary signal) |
| Euro Bkngs | Float | Not used in scoring |
| Partner | String | Target field — currently untagged |
| Technology | String | Taxonomy matching |
| Offer | String | Taxonomy matching |
| Portfolio | String | Domain context |
| Country | String | Regional partner rules (future) |
| Opty Lead | Email | Approval email recipient |
| Business Line (L1-L3) | String | Domain context |
