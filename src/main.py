"""THOR Pipeline Orchestrator — main entrypoint for the daily run.

Ties together: extract (Blob) → parse → filter → recommend (LLM) → email → Cosmos DB state.
"""

from __future__ import annotations

import json
import logging
import sys
from collections import defaultdict
from pathlib import Path

import polars as pl
import yaml

from src.approval.email_builder import (
    OpportunityRecommendation,
    PartnerCandidate,
    build_digest_email,
)
from src.approval.token_utils import generate_token
from src.audit.audit_logger import append_audit_entry
from src.engine.account_history import score_account_history
from src.engine.keyword_extractor import extract_keywords
from src.engine.recommender import recommend
from src.engine.taxonomy_mapper import load_taxonomy, match_taxonomy
from src.engine.similarity_scorer import score_similarity
from src.extract.blob_reader import download_from_blob
from src.filter.filter_untagged import filter_untagged
from src.parse.xls_parser import parse_xlsm
from src.store.state_manager import (
    get_processed_ids,
    is_email_sent,
    record_email_sent,
    record_recommendation,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_settings(path: str = "config/settings.yaml") -> dict:
    """Load application settings."""
    with open(path) as f:
        return yaml.safe_load(f)


def run_pipeline(
    file_path: Path | None = None,
    dry_run: bool = False,
    use_llm: bool = True,
) -> dict:
    """Execute the full recommendation pipeline.

    Args:
        file_path: Optional path to local .xlsm (skips Blob download).
        dry_run: If True, generate recommendations but don't send emails.
        use_llm: If True, use GPT-5.4 as primary reasoner (with fallback).

    Returns:
        Summary dict with counts and outcomes.
    """
    settings = load_settings()
    batch_size = settings["processing"]["batch_size"]
    max_batches = settings["processing"]["max_batches_per_run"]

    # ── Step 1: Extract from Azure Blob ─────────────────────────────────
    if file_path is None:
        blob_cfg = settings.get("blob", {})
        logger.info("Downloading .xlsm from Azure Blob Storage...")
        file_path = download_from_blob(
            container_name=blob_cfg.get("container_name"),
            blob_name=blob_cfg.get("blob_name"),
        )
    else:
        file_path = Path(file_path)
    logger.info(f"Using file: {file_path}")

    # ── Step 2: Parse ───────────────────────────────────────────────────
    sheet_name = settings.get("sharepoint", {}).get("sheet_name", "Sheet1")
    logger.info(f"Parsing sheet '{sheet_name}'...")
    df = parse_xlsm(file_path, sheet_name=sheet_name)
    logger.info(f"Total rows: {df.height:,}")

    # ── Step 3: Filter untagged + skip already processed (Cosmos DB) ────
    processed_ids = get_processed_ids()
    logger.info(f"Already processed: {len(processed_ids):,} opportunities")
    untagged_df = filter_untagged(df, processed_ids=processed_ids)
    logger.info(f"Untagged to process: {untagged_df.height:,}")

    if untagged_df.height == 0:
        logger.info("No new untagged opportunities. Done.")
        return {"processed": 0, "skipped": len(processed_ids), "leads_notified": 0, "emails_sent": 0, "llm_calls": 0, "llm_fallbacks": 0}

    # ── Step 4: Prepare tagged data for account history + similarity ────
    tagged_df = df.filter(
        pl.col("Partner").is_not_null()
        & ~pl.col("Partner").cast(pl.Utf8).is_in(["No Vendor/Partner", "-", ""])
    )
    logger.info(f"Tagged rows available for scoring: {tagged_df.height:,}")

    # ── Step 5: Load taxonomy ───────────────────────────────────────────
    taxonomy = load_taxonomy()
    min_deals = settings["scoring"]["min_deals_for_boost"]

    # ── Step 6: Process in batches ──────────────────────────────────────
    total_to_process = min(untagged_df.height, batch_size * max_batches)
    recommendations_by_lead: defaultdict[str, list[OpportunityRecommendation]] = defaultdict(list)
    processed_count = 0
    llm_calls = 0
    llm_fallbacks = 0

    for batch_start in range(0, total_to_process, batch_size):
        batch_end = min(batch_start + batch_size, total_to_process)
        batch = untagged_df.slice(batch_start, batch_end - batch_start)
        logger.info(f"Processing batch {batch_start // batch_size + 1}: rows {batch_start}-{batch_end}")

        for row_dict in batch.iter_rows(named=True):
            opp_id = str(row_dict.get("Opportunity ID", ""))
            opp_name = str(row_dict.get("Opportunity Name", ""))
            account_name = str(row_dict.get("Account Name", ""))
            opty_lead = str(row_dict.get("Opty Lead", ""))

            if not opp_id:
                continue

            # ── Keyword extraction (retained as first-class signal) ─────
            keywords = extract_keywords(row_dict)

            # ── Taxonomy matching ───────────────────────────────────────
            taxonomy_scores = match_taxonomy(keywords, taxonomy)

            # Track which keywords matched which partner
            keywords_by_partner: dict[str, list[str]] = {}
            rules = taxonomy.get("rules", {})
            text_joined = " ".join(keywords)
            for partner, rule in rules.items():
                matched = [kw for kw in rule.get("keywords", []) if kw.lower() in text_joined]
                if matched:
                    keywords_by_partner[partner] = matched

            # ── Similarity scoring ──────────────────────────────────────
            similarity_scores = score_similarity(row_dict, tagged_df)

            # ── Account history scoring ─────────────────────────────────
            account_history_scores = score_account_history(
                account_name, tagged_df, min_deals_for_boost=min_deals
            )

            # ── Offer/Technology exact match ────────────────────────────
            offer_match_scores = _score_offer_match(row_dict, taxonomy)

            # ── Generate recommendation (LLM-primary + fallback) ────────
            rec = recommend(
                opportunity_id=opp_id,
                taxonomy_scores=taxonomy_scores,
                similarity_scores=similarity_scores,
                account_history_scores=account_history_scores,
                offer_match_scores=offer_match_scores,
                keywords_by_partner=keywords_by_partner,
                opportunity_context=row_dict,
                keywords=keywords,
                taxonomy_context=taxonomy,
                use_llm=use_llm,
            )

            # Track LLM usage
            if use_llm:
                llm_calls += 1
                if rec.candidates and rec.candidates[0].signals.get("llm_reasoned") is not True:
                    llm_fallbacks += 1

            # ── Map to email model ──────────────────────────────────────
            euro_bkngs_raw = row_dict.get("Euro Bkngs", 0)
            euro_bkngs = float(euro_bkngs_raw) if euro_bkngs_raw else 0.0
            stage = str(row_dict.get("Stage", ""))

            opp_rec = OpportunityRecommendation(
                opp_id=opp_id,
                opp_name=opp_name,
                account_name=account_name,
                candidates=[
                    PartnerCandidate(
                        partner=c.partner,
                        confidence=c.confidence,
                        rationale=c.rationale,
                    )
                    for c in rec.candidates
                ],
                euro_bkngs=euro_bkngs,
                stage=stage,
            )

            # Group by Sales Lead email
            lead_email = opty_lead if opty_lead and "@" in opty_lead else "unassigned"
            recommendations_by_lead[lead_email].append(opp_rec)

            # ── Persist recommendation to Cosmos DB ─────────────────────
            record_recommendation(
                opp_id=opp_id,
                candidates=[
                    {"partner": c.partner, "confidence": c.confidence, "rationale": c.rationale}
                    for c in rec.candidates
                ],
                top_partner=rec.top_partner,
                top_confidence=rec.top_confidence,
            )

            # Local audit backup
            append_audit_entry(
                opportunity_id=opp_id,
                recommended_partner=rec.top_partner,
                decision="recommended",
                rationale=rec.candidates[0].rationale if rec.candidates else "",
                confidence=rec.top_confidence,
            )
            processed_count += 1

    logger.info(f"Processed {processed_count:,} opportunities")
    logger.info(f"LLM calls: {llm_calls}, fallbacks to deterministic: {llm_fallbacks}")
    logger.info(f"Grouped into {len(recommendations_by_lead)} Sales Lead digests")

    # ── Step 7: Build digest emails ───────────────────────────────────
    webhook_base = settings.get("webhook", {}).get("base_url", "https://thor-api-rcc.azurewebsites.net/api")
    digests: list[dict] = []
    for lead_email, opps in recommendations_by_lead.items():
        tokens = {opp.opp_id: generate_token(opp.opp_id) for opp in opps}
        html_content = build_digest_email(opps, webhook_base, tokens)
        _save_email_preview(lead_email, html_content)
        digests.append({
            "to": lead_email,
            "subject": f"THOR — {len(opps)} Partner Tag Recommendations for Review",
            "html": html_content,
            "opp_count": len(opps),
        })
        # Record email-sent status
        for opp in opps:
            record_email_sent(opp_id=opp.opp_id, lead_email=lead_email)

    if dry_run:
        logger.info(f"DRY RUN — saved {len(digests)} email preview(s) to data/email_previews/")
    else:
        logger.info(f"Generated {len(digests)} digest email(s) — included in response for n8n to send")

    return {
        "processed": processed_count,
        "skipped": len(processed_ids),
        "leads_notified": len(recommendations_by_lead),
        "emails_sent": len(digests),
        "llm_calls": llm_calls,
        "llm_fallbacks": llm_fallbacks,
        "digests": digests,
    }


def _score_offer_match(row: dict, taxonomy: dict) -> dict[str, float]:
    """Score exact match between Offer/Technology fields and partner taxonomy."""
    scores: dict[str, float] = {}
    offer = str(row.get("Offer", "")).lower().strip()
    tech = str(row.get("Technology", "")).lower().strip()

    if not offer and not tech:
        return scores

    rules = taxonomy.get("rules", {})
    for partner, rule in rules.items():
        partner_offers = [o.lower() for o in rule.get("offers", [])]
        partner_techs = [t.lower() for t in rule.get("technologies", [])]

        match_score = 0.0
        if offer and offer in partner_offers:
            match_score += 70.0
        if tech and tech in partner_techs:
            match_score += 30.0

        if match_score > 0:
            scores[partner] = min(match_score, 100.0)

    return scores


def _send_digest_emails(
    recommendations_by_lead: dict[str, list[OpportunityRecommendation]],
    webhook_base: str,
) -> int:
    """Build and send digest emails. Records sent status in Cosmos DB."""
    emails_sent = 0
    for lead_email, opps in recommendations_by_lead.items():
        if lead_email == "unassigned":
            logger.warning(f"Skipping {len(opps)} opps with no assigned lead")
            continue

        # Generate tokens for each opportunity
        tokens = {opp.opp_id: generate_token(opp.opp_id) for opp in opps}

        # Build HTML
        html_content = build_digest_email(opps, webhook_base, tokens)

        # TODO: Send via Microsoft Graph API
        logger.info(f"Would send digest to {lead_email}: {len(opps)} opportunities")
        _save_email_preview(lead_email, html_content)

        # Record email-sent status in Cosmos DB for each opp
        for opp in opps:
            record_email_sent(opp_id=opp.opp_id, lead_email=lead_email)

        emails_sent += 1

    return emails_sent


def _save_email_preview(lead_email: str, html_content: str) -> None:
    """Save email HTML to local file for preview/testing."""
    preview_dir = Path("data/email_previews")
    preview_dir.mkdir(parents=True, exist_ok=True)
    safe_name = lead_email.replace("@", "_at_").replace(".", "_")
    (preview_dir / f"{safe_name}.html").write_text(html_content, encoding="utf-8")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="THOR Partner Tagging Pipeline")
    parser.add_argument("--file", type=str, help="Path to local .xlsm file (skip Blob download)")
    parser.add_argument("--dry-run", action="store_true", help="Generate recommendations without sending emails")
    parser.add_argument("--no-llm", action="store_true", help="Force deterministic scoring (skip LLM)")
    parser.add_argument("--json-output", action="store_true", help="Print JSON summary to stdout (for n8n)")
    args = parser.parse_args()

    result = run_pipeline(file_path=args.file, dry_run=args.dry_run, use_llm=not args.no_llm)

    if args.json_output:
        print(json.dumps(result))
    else:
        logger.info(f"Pipeline complete: {result}")
