"""Build HTML approval emails for partner tag recommendations.

Supports two modes:
- Single opportunity email (for real-time / low-volume)
- Digest email: one email per Sales Lead with ALL their untagged opps
"""

from __future__ import annotations

from dataclasses import dataclass

from jinja2 import Template


@dataclass
class PartnerCandidate:
    """A single partner recommendation with its confidence score and rationale."""

    partner: str
    confidence: float
    rationale: str


@dataclass
class OpportunityRecommendation:
    """One opportunity with its ranked partner candidates."""

    opp_id: str
    opp_name: str
    account_name: str
    candidates: list[PartnerCandidate]


def _confidence_label(score: float) -> str:
    """Return emoji + label for confidence band."""
    if score >= 80:
        return "🟢"
    if score >= 50:
        return "🟡"
    return "🔴"


EMAIL_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Segoe UI, Arial, sans-serif; max-width: 700px; margin: auto;">
  <h2 style="color: #0078d4;">THOR — Partner Tag Recommendation</h2>
  <p>The following opportunity needs a partner tag:</p>

  <table style="border-collapse: collapse; width: 100%; margin: 16px 0;">
    <tr style="background: #f3f3f3;">
      <td style="padding: 8px; font-weight: bold;">Opportunity ID</td>
      <td style="padding: 8px;">{{ opp_id }}</td>
    </tr>
    <tr>
      <td style="padding: 8px; font-weight: bold;">Opportunity Name</td>
      <td style="padding: 8px;">{{ opp_name }}</td>
    </tr>
    <tr style="background: #f3f3f3;">
      <td style="padding: 8px; font-weight: bold;">Account</td>
      <td style="padding: 8px;">{{ account_name }}</td>
    </tr>
  </table>

  <p>Based on keyword analysis, account history, and taxonomy mapping, here are the recommended partners:</p>

  {% for candidate in candidates %}
  <div style="border: 1px solid #ddd; border-radius: 6px; padding: 12px; margin: 12px 0;{% if loop.first %} border-left: 4px solid #0078d4;{% endif %}">
    <strong>#{{ loop.index }} {{ candidate.partner }}</strong>
    <span style="float: right; font-size: 14px;">{{ candidate.label }} {{ candidate.confidence }}%</span>
    <p style="margin: 8px 0 12px 0; font-size: 13px; color: #555;">{{ candidate.rationale }}</p>
    <a href="{{ webhook_base }}/select?opp_id={{ opp_id }}&partner={{ candidate.partner }}&token={{ token }}"
       style="background: #107c10; color: white; padding: 8px 20px; text-decoration: none; border-radius: 4px; font-size: 13px;">
      ✅ Select {{ candidate.partner }}
    </a>
  </div>
  {% endfor %}

  <div style="margin: 20px 0;">
    <p style="margin-bottom: 8px;">None of these?</p>
    <a href="{{ webhook_base }}/reject?opp_id={{ opp_id }}&token={{ token }}"
       style="background: #d83b01; color: white; padding: 8px 20px; text-decoration: none; border-radius: 4px; font-size: 13px;">
      ❌ Reject All
    </a>
  </div>

  <p style="font-size: 12px; color: #888;">
    This is an automated recommendation from the THOR Agentic Partner Tagging system.
  </p>
</body>
</html>
"""


def build_approval_email(
    opp_id: str,
    opp_name: str,
    account_name: str,
    candidates: list[PartnerCandidate],
    webhook_base: str,
    token: str,
) -> str:
    """Render the multi-partner choice approval email HTML."""
    template = Template(EMAIL_TEMPLATE)
    candidate_data = [
        {
            "partner": c.partner,
            "confidence": round(c.confidence, 1),
            "rationale": c.rationale,
            "label": _confidence_label(c.confidence),
        }
        for c in candidates
    ]
    return template.render(
        opp_id=opp_id,
        opp_name=opp_name,
        account_name=account_name,
        candidates=candidate_data,
        webhook_base=webhook_base,
        token=token,
    )


# ──────────────────────────────────────────────────────────────────────
# Digest email: one email per Sales Lead with ALL their opportunities
# ──────────────────────────────────────────────────────────────────────

DIGEST_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Segoe UI, Arial, sans-serif; max-width: 750px; margin: auto;">
  <h2 style="color: #0078d4;">THOR — Partner Tag Recommendations</h2>
  <p>You have <strong>{{ opportunities|length }}</strong> opportunities that need a partner tag.
     Please review each and select the appropriate partner.</p>

  {% for opp in opportunities %}
  <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; margin: 20px 0; background: #fafafa;">
    <h3 style="margin: 0 0 8px 0; color: #333;">{{ opp.opp_name }}</h3>
    <table style="border-collapse: collapse; width: 100%; margin-bottom: 12px; font-size: 13px;">
      <tr>
        <td style="padding: 4px 8px; font-weight: bold; width: 140px;">Opportunity ID</td>
        <td style="padding: 4px 8px;">{{ opp.opp_id }}</td>
      </tr>
      <tr>
        <td style="padding: 4px 8px; font-weight: bold;">Account</td>
        <td style="padding: 4px 8px;">{{ opp.account_name }}</td>
      </tr>
    </table>

    {% for candidate in opp.candidates %}
    <div style="border-left: 3px solid {% if loop.first %}#0078d4{% else %}#ccc{% endif %}; padding: 8px 12px; margin: 8px 0; background: white;">
      <strong>#{{ loop.index }} {{ candidate.partner }}</strong>
      <span style="float: right;">{{ candidate.label }} {{ candidate.confidence }}%</span>
      <p style="margin: 4px 0; font-size: 12px; color: #555;">{{ candidate.rationale }}</p>
      <a href="{{ webhook_base }}/select?opp_id={{ opp.opp_id }}&partner={{ candidate.partner }}&token={{ opp.token }}"
         style="background: #107c10; color: white; padding: 6px 14px; text-decoration: none; border-radius: 3px; font-size: 12px;">
        ✅ Select {{ candidate.partner }}
      </a>
    </div>
    {% endfor %}

    <div style="margin-top: 10px;">
      <a href="{{ webhook_base }}/reject?opp_id={{ opp.opp_id }}&token={{ opp.token }}"
         style="background: #d83b01; color: white; padding: 6px 14px; text-decoration: none; border-radius: 3px; font-size: 12px;">
        ❌ Reject All
      </a>
    </div>
  </div>
  {% endfor %}

  <p style="font-size: 12px; color: #888; margin-top: 24px;">
    This is an automated recommendation from the THOR Agentic Partner Tagging system.
  </p>
</body>
</html>
"""


def build_digest_email(
    opportunities: list[OpportunityRecommendation],
    webhook_base: str,
    tokens: dict[str, str],
) -> str:
    """Render a digest email containing multiple opportunities for one Sales Lead.

    Args:
        opportunities: List of opportunities with their ranked candidates.
        webhook_base: Base URL for webhook callbacks.
        tokens: Dict of {opp_id: hmac_token} for secure links.

    Returns:
        Rendered HTML string.
    """
    template = Template(DIGEST_TEMPLATE)
    opp_data = []
    for opp in opportunities:
        opp_data.append({
            "opp_id": opp.opp_id,
            "opp_name": opp.opp_name,
            "account_name": opp.account_name,
            "token": tokens.get(opp.opp_id, ""),
            "candidates": [
                {
                    "partner": c.partner,
                    "confidence": round(c.confidence, 1),
                    "rationale": c.rationale,
                    "label": _confidence_label(c.confidence),
                }
                for c in opp.candidates
            ],
        })
    return template.render(
        opportunities=opp_data,
        webhook_base=webhook_base,
    )
