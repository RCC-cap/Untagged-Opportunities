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


def _humanize_rationale(raw: str, partner: str) -> str:
    """Convert internal rationale text into a clear, trust-building explanation."""
    if not raw:
        return f"Matched to {partner} based on opportunity context and partner taxonomy alignment."
    low = raw.lower()
    reasons = []
    if "account history" in low or "previously tagged" in low:
        reasons.append(f"this account was previously tagged with {partner}")
    if "keyword" in low:
        if "azure" in low:
            reasons.append("opportunity name/description contains Azure-related terms")
        elif "aws" in low:
            reasons.append("opportunity name/description contains AWS-related terms")
        elif "sap" in low:
            reasons.append("opportunity name/description references SAP technologies")
        elif "google" in low or "gcp" in low:
            reasons.append("opportunity name/description references Google Cloud")
        else:
            reasons.append(f"technology keywords in the opportunity match {partner}")
    if "taxonomy" in low or "domain" in low:
        reasons.append(f"the business domain maps to {partner} in our partner taxonomy")
    if "tier" in low or "strategic" in low:
        reasons.append(f"{partner} is a Tier-1 strategic alliance partner for this segment")
    if not reasons:
        clean = raw.split(";")[0].strip().rstrip(".")
        return f"Why {partner}: {clean}." if len(clean) < 80 else f"Matched based on multiple scoring signals."
    return f"Why {partner}: {'; '.join(reasons)}."


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
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <!--[if mso]><style>td,th{font-family:Arial,sans-serif!important}</style><![endif]-->
</head>
<body style="margin:0;padding:0;background:#f0f2f5;font-family:'Segoe UI',Roboto,Arial,sans-serif;-webkit-text-size-adjust:100%;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f2f5;padding:32px 0;">
    <tr><td align="center">
      <table width="740" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;border:1px solid #dde1e6;">

        <!-- Header -->
        <tr><td style="background:linear-gradient(135deg,#003366 0%,#0070AD 100%);padding:28px 36px;border-radius:12px 12px 0 0;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td style="color:#ffffff;font-size:20px;font-weight:700;letter-spacing:-0.3px;">Partner Tag Recommendations</td>
              <td align="right" style="color:rgba(255,255,255,0.7);font-size:11px;letter-spacing:0.3px;">THOR Automated Analysis</td>
            </tr>
          </table>
        </td></tr>

        <!-- Intro -->
        <tr><td style="padding:28px 36px 16px;">
          <p style="margin:0 0 6px;font-size:16px;color:#1a1a1a;font-weight:500;">Hi {{ lead_name }},</p>
          <p style="margin:12px 0 0;font-size:14px;color:#444;line-height:1.7;">
            I found <strong>{{ total_opps }} opportunit{{ 'y' if total_opps == 1 else 'ies' }}</strong>
            in your pipeline without a partner tag. I analyzed each one using account history,
            technology signals, and our partner taxonomy to recommend the most likely partner.
          </p>
          <p style="margin:10px 0 0;font-size:13px;color:#666;line-height:1.7;">
            Partner tags drive revenue attribution and alliance reporting.
            Only you know the deal context &mdash; please confirm or suggest a different partner below.
          </p>
        </td></tr>

        <!-- Confidence legend -->
        <tr><td style="padding:4px 36px 24px;">
          <table cellpadding="0" cellspacing="0" style="font-size:12px;color:#555;">
            <tr>
              <td style="padding-right:24px;"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#1e7e34;vertical-align:middle;margin-right:5px;"></span><strong>80%+</strong> Strong match</td>
              <td style="padding-right:24px;"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#b8860b;vertical-align:middle;margin-right:5px;"></span><strong>50-79%</strong> Good match</td>
              <td><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#c62828;vertical-align:middle;margin-right:5px;"></span><strong>&lt;50%</strong> Needs your input</td>
            </tr>
          </table>
        </td></tr>

        {% for account_name, opps in grouped.items() %}
        <!-- Account Section Header -->
        <tr><td style="padding:8px 36px 4px;">
          <table width="100%" cellpadding="0" cellspacing="0" style="border-bottom:2px solid #0070AD;margin-bottom:4px;">
            <tr>
              <td style="font-size:17px;font-weight:700;color:#003366;padding:8px 0 8px;">{{ account_name }}</td>
              <td align="right" style="font-size:12px;color:#888;padding-bottom:8px;">{{ opps|length }} opportunit{{ 'y' if opps|length == 1 else 'ies' }}</td>
            </tr>
          </table>
        </td></tr>

        {% for opp in opps %}
        <!-- Opportunity Card -->
        <tr><td style="padding:6px 36px 10px;">
          <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e4e7ec;border-radius:10px;overflow:hidden;">

            <!-- Opp name row -->
            <tr><td style="padding:14px 20px 8px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <span style="font-size:13px;color:#333;">{{ opp.opp_name }}</span>
                    {% if opp.stage %}<span style="font-size:11px;color:#999;padding-left:10px;">{{ opp.stage }}</span>{% endif %}
                  </td>
                  <td align="right" style="white-space:nowrap;">
                    {% if opp.has_recommendation %}
                    <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{{ opp.dot_color }};vertical-align:middle;margin-right:4px;"></span>
                    <span style="font-size:12px;font-weight:600;color:{{ opp.dot_color }};">{{ opp.top_confidence }}%</span>
                    {% else %}
                    <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#c62828;vertical-align:middle;margin-right:4px;"></span>
                    <span style="font-size:12px;color:#c62828;">No match</span>
                    {% endif %}
                    {% if opp.euro_bkngs > 0 %}
                    <span style="font-size:12px;color:#0070AD;font-weight:600;padding-left:14px;">&euro;{{ "{:,.0f}".format(opp.euro_bkngs) }}</span>
                    {% endif %}
                  </td>
                </tr>
              </table>
            </td></tr>

            {% if opp.has_recommendation %}
            <!-- Partner recommendation box -->
            <tr><td style="padding:2px 20px 10px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fbff;border:1px solid #dce8f5;border-radius:8px;">
                <tr><td style="padding:14px 18px;">
                  <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                      <td style="font-size:15px;font-weight:700;color:#003366;">{{ opp.top_partner }}</td>
                      <td align="right">
                        <span style="display:inline-block;background:{{ opp.top_badge_bg }};color:{{ opp.top_badge_fg }};padding:3px 12px;border-radius:12px;font-size:11px;font-weight:700;">{{ opp.top_confidence }}%</span>
                      </td>
                    </tr>
                    <tr>
                      <td colspan="2" style="font-size:13px;color:#444;padding-top:8px;line-height:1.6;">{{ opp.top_rationale }}</td>
                    </tr>
                  </table>
                </td></tr>
              </table>
            </td></tr>

            {% if opp.secondary %}
            <!-- Secondary -->
            <tr><td style="padding:0 20px 8px;">
              <span style="font-size:12px;color:#777;">Also possible: <strong>{{ opp.secondary.partner }}</strong> ({{ opp.secondary.confidence }}%)</span>
            </td></tr>
            {% endif %}

            <!-- Actions with recommendation -->
            <tr><td style="padding:4px 20px 16px;">
              <table cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <a href="{{ webhook_base }}/select?opp_id={{ opp.opp_id }}&partner={{ opp.top_partner }}&token={{ opp.token }}"
                       style="display:inline-block;background:#0070AD;color:#ffffff;padding:9px 22px;text-decoration:none;border-radius:6px;font-size:13px;font-weight:600;">
                      Accept {{ opp.top_partner }}
                    </a>
                  </td>
                  <td style="padding-left:12px;">
                    <a href="{{ webhook_base }}/suggest?opp_id={{ opp.opp_id }}&token={{ opp.token }}"
                       style="display:inline-block;background:#ffffff;color:#0070AD;padding:9px 16px;text-decoration:none;border-radius:6px;font-size:13px;font-weight:500;border:1px solid #0070AD;">
                      Suggest different
                    </a>
                  </td>
                  <td style="padding-left:12px;">
                    <a href="{{ webhook_base }}/reject?opp_id={{ opp.opp_id }}&token={{ opp.token }}"
                       style="font-size:12px;color:#999;text-decoration:none;">None apply</a>
                  </td>
                </tr>
              </table>
            </td></tr>

            {% else %}
            <!-- No valid partner -->
            <tr><td style="padding:2px 20px 10px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background:#fff8f0;border:1px solid #ffd6a0;border-radius:8px;">
                <tr><td style="padding:14px 18px;">
                  <p style="margin:0;font-size:13px;color:#7a4900;line-height:1.6;">
                    <strong>No confident match found.</strong> The analysis did not identify a clear partner for this opportunity.
                    Please suggest the correct partner based on your knowledge of this deal.
                  </p>
                </td></tr>
              </table>
            </td></tr>

            <!-- Actions without recommendation -->
            <tr><td style="padding:4px 20px 16px;">
              <table cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <a href="{{ webhook_base }}/suggest?opp_id={{ opp.opp_id }}&token={{ opp.token }}"
                       style="display:inline-block;background:#0070AD;color:#ffffff;padding:9px 22px;text-decoration:none;border-radius:6px;font-size:13px;font-weight:600;">
                      Suggest a partner
                    </a>
                  </td>
                  <td style="padding-left:12px;">
                    <a href="{{ webhook_base }}/reject?opp_id={{ opp.opp_id }}&token={{ opp.token }}"
                       style="font-size:12px;color:#999;text-decoration:none;">Skip</a>
                  </td>
                </tr>
              </table>
            </td></tr>
            {% endif %}

          </table>
        </td></tr>
        {% endfor %}

        <!-- Spacer between accounts -->
        <tr><td style="padding:10px 0;"></td></tr>
        {% endfor %}

        <!-- Footer -->
        <tr><td style="padding:20px 36px;border-top:1px solid #eee;background:#fafbfc;border-radius:0 0 12px 12px;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td style="font-size:11px;color:#999;line-height:1.6;">
                Automated by <strong style="color:#003366;">THOR</strong> Partner Tagging &middot; Capgemini Sales Operations
              </td>
              <td align="right" style="font-size:11px;color:#bbb;">{{ now }}</td>
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
    lead_name: str = "",
) -> str:
    """Render a digest email containing multiple opportunities for one Sales Lead.

    Args:
        opportunities: List of opportunities with their ranked candidates.
        webhook_base: Base URL for webhook callbacks.
        tokens: Dict of {opp_id: hmac_token} for secure links.
        lead_name: Display name for the greeting (e.g. "Riccardo").

    Returns:
        Rendered HTML string.
    """
    from collections import OrderedDict
    from datetime import datetime, timezone

    template = Template(DIGEST_TEMPLATE)

    # Group opportunities by account name (preserving order)
    grouped: OrderedDict[str, list[dict]] = OrderedDict()
    for opp in opportunities:
        top = opp.candidates[0] if opp.candidates else None
        has_recommendation = top is not None and top.partner != "Unknown" and top.confidence > 0

        if has_recommendation:
            top_conf = round(top.confidence, 1)
            dot_color = "#1e7e34" if top_conf >= 80 else "#b8860b" if top_conf >= 50 else "#c62828"
            badge_bg, badge_fg = _confidence_badge(top.confidence)
            top_rationale = _humanize_rationale(top.rationale, top.partner)
        else:
            top_conf = 0
            dot_color = "#c62828"
            badge_bg, badge_fg = "#fde7e7", "#c62828"
            top_rationale = ""

        secondary = None
        if has_recommendation and len(opp.candidates) > 1:
            c2 = opp.candidates[1]
            if c2.partner != "Unknown" and c2.confidence > 10:
                secondary = {"partner": c2.partner, "confidence": round(c2.confidence, 1)}

        opp_dict = {
            "opp_id": opp.opp_id,
            "opp_name": opp.opp_name,
            "account_name": opp.account_name,
            "euro_bkngs": opp.euro_bkngs,
            "stage": opp.stage,
            "token": tokens.get(opp.opp_id, ""),
            "has_recommendation": has_recommendation,
            "top_partner": top.partner if has_recommendation else "",
            "top_confidence": top_conf,
            "top_rationale": top_rationale,
            "top_badge_bg": badge_bg,
            "top_badge_fg": badge_fg,
            "dot_color": dot_color,
            "secondary": secondary,
        }
        grouped.setdefault(opp.account_name, []).append(opp_dict)

    return template.render(
        grouped=grouped,
        webhook_base=webhook_base,
        lead_name=lead_name or "Sales Lead",
        total_opps=len(opportunities),
        now=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
