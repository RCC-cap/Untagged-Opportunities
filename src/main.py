"""THOR Pipeline Orchestrator — main entrypoint for the daily run.

Ties together: extract → parse → filter → recommend → email → audit.
"""

from __future__ import annotations

import logging
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
from src.audit.audit_logger import append_audit_entry, get_processed_ids
from src.engine.account_history import score_account_history
from src.engine.keyword_extractor import extract_keywords
from src.engine.recommender import recommend
from src.engine.taxonomy_mapper import load_taxonomy, match_taxonomy
from src.engine.similarity_scorer import score_similarity
from src.extract.sharepoint_reader import download_xlsm
from src.filter.filter_untagged import filter_untagged
from src.parse.xls_parser import parse_xlsm

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_settings(path: str = "config/settings.yaml") -> dict:
    """Load application settings."""
    with open(path) as f:
        return yaml.safe_load(f)


def run_pipeline(
    file_path: Path | None = None,
    dry_run: bool = False,
) -> dict:
    """Execute the full recommendation pipeline.

    Args:
        file_path: Optional path to local .xlsm (skips SharePoint download).
        dry_run: If True, generate recommendations but don't send emails.

    Returns:
        Summary dict with counts and outcomes.
    """
    settings = load_settings()
    batch_size = settings["processing"]["batch_size"]
    max_batches = settings["processing"]["max_batches_per_run"]

    # ── Step 1: Extract ─────────────────────────────────────────────────
    if file_path is None:
        logger.info("Downloading .xlsm from SharePoint...")
        file_path = download_xlsm()
    else:
        file_path = Path(file_path)
    logger.info(f"Using file: {file_path}")

    # ── Step 2: Parse ───────────────────────────────────────────────────
    sheet_name = settings["sharepoint"]["sheet_name"]
    logger.info(f"Parsing sheet '{sheet_name}'...")
    df = parse_xlsm(file_path, sheet_name=sheet_name)
    logger.info(f"Total rows: {df.height:,}")

    # ── Step 3: Filter untagged + skip already processed ────────────────
    processed_ids = get_processed_ids()
    logger.info(f"Already processed: {len(processed_ids):,} opportunities")
    untagged_df = filter_untagged(df, processed_ids=processed_ids)
    logger.info(f"Untagged to process: {untagged_df.height:,}")

    if untagged_df.height == 0:
        logger.info("No new untagged opportunities. Done.")
        return {"processed": 0, "skipped": len(processed_ids)}

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

    for batch_start in range(0, total_to_process, batch_size):
        batch_end = min(batch_start + batch_size, total_to_process)
        batch = untagged_df.slice(batch_start, batch_end - batch_start)
        logger.info(f"Processing batch {batch_start // batch_size + 1}: rows {batch_start}-{batch_end}")

        for row_dict in batch.iter_rows(named=True):
            opp_id = str(row_dict.get("Opportunity ID", ""))
            opp_name = str(row_dict.get("Opportunity Name", ""))
            account_name = str(row_dict.get("Account Name", ""))
            opty_lead = str(row_dict.get("Opty Lead", ""))

            # Skip if no OppID or no lead
            if not opp_id:
                continue

            # Keyword extraction
            keywords = extract_keywords(row_dict)

            # Taxonomy matching
            taxonomy_scores = match_taxonomy(keywords, taxonomy)

            # Track which keywords matched which partner
            keywords_by_partner: dict[str, list[str]] = {}
            rules = taxonomy.get("rules", {})
            text_joined = " ".join(keywords)
            for partner, rule in rules.items():
                matched = [kw for kw in rule.get("keywords", []) if kw.lower() in text_joined]
                if matched:
                    keywords_by_partner[partner] = matched

            # Similarity scoring
            similarity_scores = score_similarity(row_dict, tagged_df)

            # Account history scoring
            account_history_scores = score_account_history(
                account_name, tagged_df, min_deals_for_boost=min_deals
            )

            # Offer/Technology exact match
            offer_match_scores = _score_offer_match(row_dict, taxonomy)

            # Generate recommendation
            rec = recommend(
                opportunity_id=opp_id,
                taxonomy_scores=taxonomy_scores,
                similarity_scores=similarity_scores,
                account_history_scores=account_history_scores,
                offer_match_scores=offer_match_scores,
                keywords_by_partner=keywords_by_partner,
            )

            # Map to email model
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
            )

            # Group by Sales Lead email
            lead_email = opty_lead if opty_lead and "@" in opty_lead else "unassigned"
            recommendations_by_lead[lead_email].append(opp_rec)

            # Audit: log the recommendation
            append_audit_entry(
                opportunity_id=opp_id,
                recommended_partner=rec.top_partner,
                decision="recommended",
                rationale=rec.candidates[0].rationale if rec.candidates else "",
                confidence=rec.top_confidence,
            )
            processed_count += 1

    logger.info(f"Processed {processed_count:,} opportunities")
    logger.info(f"Grouped into {len(recommendations_by_lead)} Sales Lead digests")

    # ── Step 7: Build and send digest emails ────────────────────────────
    if not dry_run:
        webhook_base = settings.get("webhook", {}).get("base_url", "https://thor.example.com/api")
        emails_sent = _send_digest_emails(recommendations_by_lead, webhook_base)
    else:
        emails_sent = 0
        logger.info("DRY RUN — no emails sent")

    return {
        "processed": processed_count,
        "skipped": len(processed_ids),
        "leads_notified": len(recommendations_by_lead),
        "emails_sent": emails_sent,
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
    """Build and send digest emails (placeholder — actual send via Graph API)."""
    emails_sent = 0
    for lead_email, opps in recommendations_by_lead.items():
        if lead_email == "unassigned":
            logger.warning(f"Skipping {len(opps)} opps with no assigned lead")
            continue

        # Generate tokens for each opportunity
        tokens = {opp.opp_id: generate_token(opp.opp_id) for opp in opps}

        # Build HTML
        html = build_digest_email(opps, webhook_base, tokens)

        # TODO: Send via Microsoft Graph API
        # For now, log and save locally for testing
        logger.info(f"Would send digest to {lead_email}: {len(opps)} opportunities")
        _save_email_preview(lead_email, html)
        emails_sent += 1

    return emails_sent


def _save_email_preview(lead_email: str, html: str) -> None:
    """Save email HTML to local file for preview/testing."""
    preview_dir = Path("data/email_previews")
    preview_dir.mkdir(parents=True, exist_ok=True)
    safe_name = lead_email.replace("@", "_at_").replace(".", "_")
    (preview_dir / f"{safe_name}.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="THOR Partner Tagging Pipeline")
    parser.add_argument("--file", type=str, help="Path to local .xlsm file (skip SharePoint)")
    parser.add_argument("--dry-run", action="store_true", help="Generate recommendations without sending emails")
    args = parser.parse_args()

    result = run_pipeline(file_path=args.file, dry_run=args.dry_run)
    logger.info(f"Pipeline complete: {result}")
