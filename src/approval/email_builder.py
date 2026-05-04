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
    euro_bkngs: float = 0.0
    stage: str = ""


def _confidence_label(score: float) -> str:
    """Return emoji + label for confidence band."""
    if score >= 80:
        return "🟢"
    if score >= 50:
        return "🟡"
    return "🔴"


def _confidence_badge(score: float) -> tuple[str, str]:
    """Return (background_color, text_color) for confidence badge."""
    if score >= 80:
        return ("#e6f4ea", "#1e7e34")
    if score >= 50:
        return ("#fff8e1", "#b8860b")
    if score >= 30:
        return ("#fff3e0", "#e65100")
    return ("#fde7e7", "#c62828")


EMAIL_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin: 0; padding: 0; background: #f4f5f7; font-family: 'Segoe UI', Roboto, Arial, sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background: #f4f5f7; padding: 24px 0;">
    <tr><td align="center">
      <table width="680" cellpadding="0" cellspacing="0" style="background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">

        <!-- Header -->
        <tr><td style="background: linear-gradient(135deg, #0070AD 0%, #12ABDB 100%); padding: 28px 32px;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td style="color: white; font-size: 22px; font-weight: 600; letter-spacing: -0.3px;">THOR</td>
              <td align="right" style="color: rgba(255,255,255,0.85); font-size: 12px; letter-spacing: 0.5px;">PARTNER TAGGING</td>
            </tr>
            <tr>
              <td colspan="2" style="color: rgba(255,255,255,0.9); font-size: 13px; padding-top: 6px;">Partner Tag Recommendation</td>
            </tr>
          </table>
        </td></tr>

        <!-- Body -->
        <tr><td style="padding: 28px 32px;">
          <p style="margin: 0 0 20px; color: #333; font-size: 14px; line-height: 1.6;">
            The following opportunity needs a partner tag. Please review the AI-generated recommendations and select the best-fit partner.
          </p>

          <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px; border: 1px solid #e8eaed; border-radius: 6px; overflow: hidden;">
            <tr style="background: #f8f9fb;">
              <td style="padding: 10px 14px; font-weight: 600; color: #555; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; width: 160px;">Opportunity ID</td>
              <td style="padding: 10px 14px; color: #222; font-size: 14px;">{{ opp_id }}</td>
            </tr>
            <tr>
              <td style="padding: 10px 14px; font-weight: 600; color: #555; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; border-top: 1px solid #eee;">Opportunity</td>
              <td style="padding: 10px 14px; color: #222; font-size: 14px; font-weight: 500; border-top: 1px solid #eee;">{{ opp_name }}</td>
            </tr>
            <tr style="background: #f8f9fb;">
              <td style="padding: 10px 14px; font-weight: 600; color: #555; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; border-top: 1px solid #eee;">Account</td>
              <td style="padding: 10px 14px; color: #222; font-size: 14px; border-top: 1px solid #eee;">{{ account_name }}</td>
            </tr>
          </table>

          <p style="margin: 0 0 16px; color: #555; font-size: 13px;">Recommended partners (ranked by confidence):</p>

          {% for candidate in candidates %}
          <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 12px; border: 1px solid {% if loop.first %}#0070AD{% else %}#e0e0e0{% endif %}; border-radius: 6px; overflow: hidden;">
            <tr>
              <td style="background: {% if loop.first %}#0070AD{% else %}#f8f9fb{% endif %}; padding: 14px 16px;">
                <table width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td style="color: {% if loop.first %}white{% else %}#333{% endif %}; font-size: 15px; font-weight: 600;">
                      #{{ loop.index }} {{ candidate.partner }}
                    </td>
                    <td align="right">
                      <span style="display: inline-block; background: {{ candidate.badge_bg }}; color: {{ candidate.badge_fg }}; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600;">
                        {{ candidate.confidence }}%
                      </span>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding: 12px 16px; background: white;">
                <p style="margin: 0 0 12px; font-size: 13px; color: #666; line-height: 1.5;">{{ candidate.rationale }}</p>
                <a href="{{ webhook_base }}/select?opp_id={{ opp_id }}&partner={{ candidate.partner }}&token={{ token }}"
                   style="display: inline-block; background: #0070AD; color: white; padding: 10px 24px; text-decoration: none; border-radius: 4px; font-size: 13px; font-weight: 600;">
                  Select {{ candidate.partner }}
                </a>
              </td>
            </tr>
          </table>
          {% endfor %}

          <table width="100%" cellpadding="0" cellspacing="0" style="margin-top: 20px; border-top: 1px solid #eee; padding-top: 16px;">
            <tr>
              <td>
                <p style="margin: 0 0 8px; font-size: 12px; color: #888;">None of these match?</p>
                <a href="{{ webhook_base }}/reject?opp_id={{ opp_id }}&token={{ token }}"
                   style="display: inline-block; background: white; color: #d83b01; padding: 9px 22px; text-decoration: none; border-radius: 4px; font-size: 13px; font-weight: 600; border: 1px solid #d83b01;">
                  Reject All
                </a>
              </td>
            </tr>
          </table>
        </td></tr>

        <!-- Footer -->
        <tr><td style="background: #f8f9fb; padding: 16px 32px; border-top: 1px solid #eee;">
          <p style="margin: 0; font-size: 11px; color: #999; line-height: 1.6;">
            Automated recommendation by <strong style="color: #0070AD;">THOR</strong> Agentic Partner Tagging &mdash; Capgemini Sales Operations
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
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
            "badge_bg": _confidence_badge(c.confidence)[0],
            "badge_fg": _confidence_badge(c.confidence)[1],
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
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin: 0; padding: 0; background: #f4f5f7; font-family: 'Segoe UI', Roboto, Arial, sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background: #f4f5f7; padding: 24px 0;">
    <tr><td align="center">
      <table width="680" cellpadding="0" cellspacing="0" style="background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">

        <!-- Header -->
        <tr><td style="background: linear-gradient(135deg, #0070AD 0%, #12ABDB 100%); padding: 28px 32px;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td style="color: white; font-size: 22px; font-weight: 600; letter-spacing: -0.3px;">THOR</td>
              <td align="right" style="color: rgba(255,255,255,0.85); font-size: 12px; letter-spacing: 0.5px;">PARTNER TAGGING</td>
            </tr>
            <tr>
              <td colspan="2" style="color: rgba(255,255,255,0.9); font-size: 13px; padding-top: 6px;">Daily Partner Tag Recommendations</td>
            </tr>
          </table>
        </td></tr>

        <!-- Summary bar -->
        <tr><td style="background: #EAF6FD; padding: 14px 32px; border-bottom: 1px solid #d0e8f5;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td style="font-size: 13px; color: #0070AD; font-weight: 600;">
                {{ opportunities|length }} opportunit{{ 'y' if opportunities|length == 1 else 'ies' }} awaiting review
              </td>
              <td align="right" style="font-size: 12px; color: #666;">
                {% set total_value = opportunities|sum(attribute='euro_bkngs') %}
                {% if total_value > 0 %}Total value: &euro;{{ "{:,.0f}".format(total_value) }}{% endif %}
              </td>
            </tr>
          </table>
        </td></tr>

        <!-- Body -->
        <tr><td style="padding: 24px 32px 8px;">
          <p style="margin: 0 0 4px; color: #555; font-size: 13px; line-height: 1.6;">
            Review each opportunity below and select the best-fit partner, or reject if none apply.
          </p>
        </td></tr>

        {% for opp in opportunities %}
        <!-- Opportunity Card -->
        <tr><td style="padding: 8px 32px 16px;">
          <table width="100%" cellpadding="0" cellspacing="0" style="border: 1px solid #e0e3e8; border-radius: 8px; overflow: hidden;">

            <!-- Card header -->
            <tr><td style="background: #f8f9fb; padding: 14px 18px; border-bottom: 1px solid #e0e3e8;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="font-size: 15px; font-weight: 600; color: #222;">{{ opp.opp_name }}</td>
                  {% if opp.euro_bkngs > 0 %}
                  <td align="right" style="font-size: 14px; font-weight: 600; color: #0070AD;">&euro;{{ "{:,.0f}".format(opp.euro_bkngs) }}</td>
                  {% endif %}
                </tr>
              </table>
            </td></tr>

            <!-- Card meta -->
            <tr><td style="padding: 12px 18px 8px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="font-size: 12px; color: #777;">
                <tr>
                  <td style="padding: 2px 0;"><span style="color: #999;">ID:</span> <strong style="color: #444;">{{ opp.opp_id }}</strong></td>
                  <td style="padding: 2px 0;"><span style="color: #999;">Account:</span> <strong style="color: #444;">{{ opp.account_name }}</strong></td>
                  {% if opp.stage %}<td style="padding: 2px 0;"><span style="color: #999;">Stage:</span> <strong style="color: #444;">{{ opp.stage }}</strong></td>{% endif %}
                </tr>
              </table>
            </td></tr>

            <!-- Candidates -->
            {% for candidate in opp.candidates %}
            <tr><td style="padding: 6px 18px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="border: 1px solid {% if loop.first %}#0070AD{% else %}#e0e0e0{% endif %}; border-radius: 6px; overflow: hidden;">
                <tr>
                  <td style="background: {% if loop.first %}#0070AD{% else %}#f8f9fb{% endif %}; padding: 10px 14px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="color: {% if loop.first %}white{% else %}#333{% endif %}; font-size: 14px; font-weight: 600;">
                          #{{ loop.index }} {{ candidate.partner }}
                        </td>
                        <td align="right">
                          <span style="display: inline-block; background: {{ candidate.badge_bg }}; color: {{ candidate.badge_fg }}; padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 700;">
                            {{ candidate.confidence }}%
                          </span>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr>
                  <td style="padding: 10px 14px; background: white;">
                    <p style="margin: 0 0 10px; font-size: 12px; color: #666; line-height: 1.5;">{{ candidate.rationale }}</p>
                    <a href="{{ webhook_base }}/select?opp_id={{ opp.opp_id }}&partner={{ candidate.partner }}&token={{ opp.token }}"
                       style="display: inline-block; background: #0070AD; color: white; padding: 9px 22px; text-decoration: none; border-radius: 4px; font-size: 13px; font-weight: 600;">
                      Select {{ candidate.partner }}
                    </a>
                  </td>
                </tr>
              </table>
            </td></tr>
            {% endfor %}

            <!-- Reject -->
            <tr><td style="padding: 10px 18px 14px;">
              <a href="{{ webhook_base }}/reject?opp_id={{ opp.opp_id }}&token={{ opp.token }}"
                 style="display: inline-block; background: white; color: #d83b01; padding: 8px 20px; text-decoration: none; border-radius: 4px; font-size: 12px; font-weight: 600; border: 1px solid #d83b01;">
                Reject All
              </a>
            </td></tr>

          </table>
        </td></tr>
        {% endfor %}

        <!-- Footer -->
        <tr><td style="background: #f8f9fb; padding: 18px 32px; border-top: 1px solid #eee;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td style="font-size: 11px; color: #999; line-height: 1.6;">
                Automated recommendation by <strong style="color: #0070AD;">THOR</strong> Agentic Partner Tagging<br>
                Capgemini Sales Operations
              </td>
              <td align="right" style="font-size: 11px; color: #bbb;">
                {{ now }}
              </td>
            </tr>
          </table>
        </td></tr>

      </table>
    </td></tr>
  </table>
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
    from datetime import datetime, timezone

    template = Template(DIGEST_TEMPLATE)
    opp_data = []
    for opp in opportunities:
        opp_data.append({
            "opp_id": opp.opp_id,
            "opp_name": opp.opp_name,
            "account_name": opp.account_name,
            "euro_bkngs": opp.euro_bkngs,
            "stage": opp.stage,
            "token": tokens.get(opp.opp_id, ""),
            "candidates": [
                {
                    "partner": c.partner,
                    "confidence": round(c.confidence, 1),
                    "rationale": c.rationale,
                    "label": _confidence_label(c.confidence),
                    "badge_bg": _confidence_badge(c.confidence)[0],
                    "badge_fg": _confidence_badge(c.confidence)[1],
                }
                for c in opp.candidates
            ],
        })
    return template.render(
        opportunities=opp_data,
        webhook_base=webhook_base,
        now=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
