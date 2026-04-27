"""Basic tests for the engine modules."""

from src.engine.keyword_extractor import extract_keywords
from src.engine.taxonomy_mapper import match_taxonomy, load_taxonomy
from src.engine.recommender import recommend, Recommendation


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


def test_taxonomy_match_microsoft():
    keywords = ["azure", "cloud", "migration", "infrastructure"]
    scores = match_taxonomy(keywords)
    assert "Microsoft" in scores
    assert scores["Microsoft"] > 0


def test_recommend_returns_recommendation():
    rec = recommend(
        opportunity_id="OPP-001",
        taxonomy_scores={"Microsoft": 80, "AWS": 20},
        similarity_scores={"Microsoft": 70, "SAP": 30},
        rationale="Strong Azure keyword signal",
    )
    assert isinstance(rec, Recommendation)
    assert rec.primary_partner == "Microsoft"
    assert rec.confidence > 0
