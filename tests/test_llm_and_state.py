"""Tests for LLM reasoner, Blob reader, and state manager."""

import json
from unittest.mock import patch, MagicMock

from src.engine.llm_reasoner import (
    LLMCandidate,
    _parse_response,
    _parse_batch_response,
    _build_user_message,
    reason_partners,
)


# ── LLM Response Parsing ──────────────────────────────────────────────


def test_parse_response_valid():
    content = json.dumps({
        "candidates": [
            {"partner": "Microsoft", "confidence": 85, "rationale": "Strong Azure signals"},
            {"partner": "AWS", "confidence": 42, "rationale": "Generic cloud terms"},
        ],
        "reasoning": "Account history strongly favours Microsoft",
    })
    result = _parse_response(content)
    assert result is not None
    assert len(result) == 2
    assert result[0].partner == "Microsoft"
    assert result[0].confidence == 85
    assert result[1].partner == "AWS"


def test_parse_response_empty_candidates():
    content = json.dumps({"candidates": [], "reasoning": "No evidence"})
    result = _parse_response(content)
    assert result is None


def test_parse_response_invalid_json():
    result = _parse_response("not json at all")
    assert result is None


def test_parse_response_missing_fields():
    content = json.dumps({"candidates": [{"partner": "SAP"}]})
    result = _parse_response(content)
    assert result is not None
    assert result[0].partner == "SAP"
    assert result[0].confidence == 0


def test_parse_batch_response_valid():
    content = json.dumps({
        "results": [
            {
                "opp_id": "OPP-001",
                "candidates": [{"partner": "Microsoft", "confidence": 80, "rationale": "..."}],
                "reasoning": "...",
            },
            {
                "opp_id": "OPP-002",
                "candidates": [{"partner": "SAP", "confidence": 70, "rationale": "..."}],
                "reasoning": "...",
            },
        ]
    })
    results = _parse_batch_response(content, 2)
    assert len(results) == 2
    assert results[0][0].partner == "Microsoft"
    assert results[1][0].partner == "SAP"


def test_parse_batch_response_pads_missing():
    content = json.dumps({"results": [{"candidates": [{"partner": "X", "confidence": 50, "rationale": "y"}]}]})
    results = _parse_batch_response(content, 3)
    assert len(results) == 3
    assert results[0] is not None
    assert results[1] is None
    assert results[2] is None


# ── User Message Building ─────────────────────────────────────────────


def test_build_user_message_structure():
    opportunity = {
        "Opportunity ID": "OPP-123",
        "Opportunity Name": "Cloud Migration",
        "Account Name": "Contoso",
        "Offer": "Azure Migration",
        "Technology": "Cloud",
        "Portfolio": "Hybrid Cloud",
        "Sector": "Manufacturing",
        "Country": "Germany",
    }
    msg = _build_user_message(
        opportunity=opportunity,
        keywords=["azure", "cloud", "migration"],
        taxonomy_scores={"Microsoft": 80, "AWS": 30},
        similarity_scores={"Microsoft": 60},
        account_history_scores={"Microsoft": 90},
        offer_match_scores={"Microsoft": 70},
        keywords_by_partner={"Microsoft": ["azure", "migration"]},
    )
    data = json.loads(msg)
    assert data["opportunity"]["id"] == "OPP-123"
    assert data["extracted_keywords"] == ["azure", "cloud", "migration"]
    assert data["signals"]["taxonomy_scores"]["Microsoft"] == 80
    assert data["keywords_matched_per_partner"]["Microsoft"] == ["azure", "migration"]


# ── LLM Integration (mocked) ─────────────────────────────────────────


@patch("src.engine.llm_reasoner._get_client")
def test_reason_partners_success(mock_get_client):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "candidates": [
            {"partner": "Microsoft", "confidence": 88, "rationale": "Strong Azure + account history"},
        ],
        "reasoning": "All signals converge on Microsoft",
    })
    mock_client.chat.completions.create.return_value = mock_response
    mock_get_client.return_value = mock_client

    result = reason_partners(
        opportunity={"Opportunity ID": "OPP-001", "Opportunity Name": "Azure Stuff"},
        keywords=["azure"],
        taxonomy_scores={"Microsoft": 80},
        similarity_scores={},
        account_history_scores={},
        offer_match_scores={},
        keywords_by_partner={"Microsoft": ["azure"]},
    )

    assert result is not None
    assert result[0].partner == "Microsoft"
    assert result[0].confidence == 88
    mock_client.chat.completions.create.assert_called_once()


@patch("src.engine.llm_reasoner._get_client")
def test_reason_partners_api_failure(mock_get_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API timeout")
    mock_get_client.return_value = mock_client

    result = reason_partners(
        opportunity={"Opportunity ID": "OPP-002"},
        keywords=[],
        taxonomy_scores={},
        similarity_scores={},
        account_history_scores={},
        offer_match_scores={},
        keywords_by_partner={},
    )

    assert result is None  # Graceful failure → caller falls back to deterministic


# ── Recommender LLM+Fallback Integration ──────────────────────────────


@patch("src.engine.recommender.reason_partners")
def test_recommend_uses_llm_when_available(mock_reason):
    from src.engine.recommender import recommend

    mock_reason.return_value = [
        LLMCandidate(partner="SAP", confidence=75, rationale="S/4HANA keywords"),
    ]

    rec = recommend(
        opportunity_id="OPP-LLM-01",
        taxonomy_scores={"SAP": 60},
        similarity_scores={},
        opportunity_context={"Opportunity ID": "OPP-LLM-01", "Opportunity Name": "SAP Migration"},
        keywords=["sap", "s4hana"],
        use_llm=True,
    )

    assert rec.top_partner == "SAP"
    assert rec.candidates[0].signals.get("llm_reasoned") is True
    mock_reason.assert_called_once()


@patch("src.engine.recommender.reason_partners")
def test_recommend_falls_back_on_llm_failure(mock_reason):
    from src.engine.recommender import recommend

    mock_reason.return_value = None  # LLM failed

    rec = recommend(
        opportunity_id="OPP-FALL-01",
        taxonomy_scores={"Microsoft": 80, "AWS": 40},
        similarity_scores={"Microsoft": 70},
        opportunity_context={"Opportunity ID": "OPP-FALL-01"},
        keywords=["azure"],
        use_llm=True,
    )

    # Should fall back to deterministic and still produce results
    assert rec.top_partner == "Microsoft"
    assert rec.candidates[0].signals.get("llm_reasoned") is not True


def test_recommend_no_llm_flag():
    from src.engine.recommender import recommend

    rec = recommend(
        opportunity_id="OPP-NOLLM",
        taxonomy_scores={"Oracle": 60},
        similarity_scores={"Oracle": 50},
        opportunity_context={"Opportunity ID": "OPP-NOLLM"},
        keywords=["oracle"],
        use_llm=False,
    )

    assert rec.top_partner == "Oracle"
    # Should not have llm_reasoned flag
    assert rec.candidates[0].signals.get("llm_reasoned") is not True
