"""Tests for the engine modules."""

import polars as pl

from src.engine.keyword_extractor import extract_keywords
from src.engine.taxonomy_mapper import match_taxonomy, load_taxonomy
from src.engine.recommender import recommend, Recommendation, PartnerCandidate
from src.engine.account_history import score_account_history


# ── Keyword Extractor ──────────────────────────────────────────────────

def test_extract_keywords_basic():
    row = {
        "Opportunity Name": "Azure Cloud Migration for Contoso",
        "Offer": "Cloud Infrastructure",
        "Portfolio": "Hybrid Cloud",
        "Technology": "Azure",
    }
    keywords = extract_keywords(row)
    assert "azure" in keywords
    assert "cloud" in keywords
    assert "migration" in keywords


def test_extract_keywords_deduplicates():
    row = {
        "Opportunity Name": "Azure Azure Azure",
        "Offer": "",
        "Portfolio": "",
        "Technology": "",
    }
    keywords = extract_keywords(row)
    assert keywords.count("azure") == 1


def test_extract_keywords_handles_empty():
    row = {"Opportunity Name": "", "Offer": None, "Portfolio": "", "Technology": ""}
    keywords = extract_keywords(row)
    assert keywords == []


# ── Taxonomy Mapper ────────────────────────────────────────────────────

def test_taxonomy_match_microsoft():
    keywords = ["azure", "cloud", "migration", "infrastructure"]
    scores = match_taxonomy(keywords)
    assert "Microsoft" in scores
    assert scores["Microsoft"] > 0


def test_taxonomy_match_sap():
    keywords = ["sap", "s/4hana", "abap", "fiori"]
    scores = match_taxonomy(keywords)
    assert "SAP" in scores
    assert scores["SAP"] > scores.get("Microsoft", 0)


def test_taxonomy_no_match():
    keywords = ["xyzzy", "plugh", "qwerty"]
    scores = match_taxonomy(keywords)
    assert len(scores) == 0


# ── Recommender (multi-candidate) ─────────────────────────────────────

def test_recommend_returns_ranked_candidates():
    rec = recommend(
        opportunity_id="OPP-001",
        taxonomy_scores={"Microsoft": 80, "AWS": 40, "Google": 10},
        similarity_scores={"Microsoft": 70, "SAP": 30},
        account_history_scores={"Microsoft": 90, "AWS": 20},
    )
    assert isinstance(rec, Recommendation)
    assert len(rec.candidates) > 0
    assert rec.candidates[0].partner == "Microsoft"
    assert rec.top_partner == "Microsoft"
    assert rec.top_confidence > rec.candidates[-1].confidence


def test_recommend_max_candidates():
    rec = recommend(
        opportunity_id="OPP-002",
        taxonomy_scores={"A": 80, "B": 60, "C": 50, "D": 40, "E": 30, "F": 20},
        similarity_scores={},
        max_candidates=3,
    )
    assert len(rec.candidates) <= 3


def test_recommend_empty_scores():
    rec = recommend(
        opportunity_id="OPP-003",
        taxonomy_scores={},
        similarity_scores={},
    )
    assert isinstance(rec, Recommendation)
    assert len(rec.candidates) == 0
    assert rec.top_partner == "Unknown"
    assert rec.top_confidence == 0.0


def test_recommend_candidates_have_rationale():
    rec = recommend(
        opportunity_id="OPP-004",
        taxonomy_scores={"Microsoft": 80},
        similarity_scores={"Microsoft": 50},
        keywords_by_partner={"Microsoft": ["azure", "migration"]},
    )
    assert rec.candidates[0].rationale != ""
    assert "azure" in rec.candidates[0].rationale.lower() or "keyword" in rec.candidates[0].rationale.lower()


# ── Account History ────────────────────────────────────────────────────

def test_account_history_basic():
    tagged_df = pl.DataFrame({
        "Account Name": ["Contoso", "Contoso", "Contoso", "Contoso", "Other"],
        "Partner": ["Microsoft", "Microsoft", "Microsoft", "AWS", "SAP"],
    })
    scores = score_account_history("Contoso", tagged_df)
    assert "Microsoft" in scores
    assert scores["Microsoft"] > scores.get("AWS", 0)
    assert scores["Microsoft"] == 75.0  # 3/4 = 75%


def test_account_history_no_deals():
    tagged_df = pl.DataFrame({
        "Account Name": ["Other Co"],
        "Partner": ["Microsoft"],
    })
    scores = score_account_history("Contoso", tagged_df)
    assert scores == {}


def test_account_history_below_min_deals():
    tagged_df = pl.DataFrame({
        "Account Name": ["Contoso"],
        "Partner": ["Microsoft"],
    })
    # min_deals_for_boost=2, only 1 deal exists
    scores = score_account_history("Contoso", tagged_df, min_deals_for_boost=2)
    assert scores == {}


def test_account_history_skips_untagged():
    tagged_df = pl.DataFrame({
        "Account Name": ["Contoso", "Contoso", "Contoso"],
        "Partner": ["Microsoft", "No Vendor/Partner", "-"],
    })
    scores = score_account_history("Contoso", tagged_df, min_deals_for_boost=1)
    assert "Microsoft" in scores
    assert "No Vendor/Partner" not in scores
