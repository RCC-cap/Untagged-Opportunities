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
    web_insight: str = ""


def _num_to_word(n: int) -> str:
    """Convert small integers to words for email readability."""
    words = {
        1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
        6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
        11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen", 15: "fifteen",
        16: "sixteen", 17: "seventeen", 18: "eighteen", 19: "nineteen", 20: "twenty",
    }
    return words.get(n, str(n))


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
              <td style="color: white; font-size: 18px; font-weight: 600; letter-spacing: -0.3px;">Thor Partner Tagging Agent</td>
              <td align="right" style="color: rgba(255,255,255,0.85); font-size: 12px; letter-spacing: 0.5px;">RECOMMENDATIONS</td>
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
                <a href="{{ webhook_base }}/select?opp_id={{ opp_id }}&amp;partner={{ candidate.partner }}&amp;token={{ token }}"
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
                <a href="{{ webhook_base }}/suggest?opp_id={{ opp_id }}&amp;token={{ token }}"
                   style="display: inline-block; background: white; color: #0070AD; padding: 9px 22px; text-decoration: none; border-radius: 4px; font-size: 13px; font-weight: 600; border: 1px solid #0070AD;">
                  Suggest a Partner
                </a>
                &nbsp;&nbsp;
                <a href="{{ webhook_base }}/comment?opp_id={{ opp_id }}&amp;token={{ token }}"
                   style="font-size: 12px; color: #8b949e; text-decoration: none;">
                  Add comment
                </a>
              </td>
            </tr>
          </table>
        </td></tr>

        <!-- Footer -->
        <tr><td style="background: #f8f9fb; padding: 16px 32px; border-top: 1px solid #eee;">
          <p style="margin: 0; font-size: 11px; color: #999; line-height: 1.6;">
            Powered by <strong style="color: #0070AD;">Capgemini Alliance Team &amp; Invent Switzerland</strong>
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
  <!--[if mso]><style>td,th,p,span,a{font-family:Arial,sans-serif!important;font-size:14px!important}</style><![endif]-->
</head>
<body style="margin:0;padding:0;background:#eef2f6;font-family:'Segoe UI',Roboto,Arial,sans-serif;font-size:14px;color:#24292f;-webkit-text-size-adjust:100%;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#eef2f6;padding:34px 16px;">
    <tr><td align="center">
      <table width="640" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:22px;overflow:hidden;box-shadow:0 24px 60px rgba(15,56,91,0.10);">

        <tr>
          <td style="background:#355c8a;padding:0;color:#ffffff;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background:linear-gradient(135deg,#5f7896 0%,#355c8a 46%,#2a5aa6 100%);">
              <tr>
                <td style="padding:26px 34px 14px;">
                  <div style="font-size:13px;font-weight:700;letter-spacing:0.02em;color:#ffffff;">Capgemini</div>
                </td>
              </tr>
              <tr>
                <td style="padding:0 34px 8px;">
                  <div style="font-size:18px;line-height:1.35;color:#7ce3ff;">Thor Partner Tagging Agent</div>
                  <div style="margin-top:10px;font-size:30px;line-height:1.2;font-weight:700;max-width:470px;color:#ffffff;">
                    Review partner recommendations in your browser workspace
                  </div>
                </td>
              </tr>
              <tr>
                <td style="padding:10px 34px 0;">
                  <div style="height:12px;background:#19d6df;width:72%;max-width:420px;"></div>
                </td>
              </tr>
              <tr>
                <td style="padding:18px 34px 26px;font-size:14px;line-height:1.7;color:rgba(255,255,255,0.92);">
                  Hi {{ lead_name }}, you are identified as <strong>Opty Lead</strong> for <strong>{{ total_opps_word }}</strong>
                  opportunit{{ 'y' if total_opps == 1 else 'ies' }} requiring partner review.
                  {% if total_booking > 0 %}Total pipeline value: <strong>&euro;{{ "{:,.0f}".format(total_booking) }}</strong>.{% endif %}
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <tr>
          <td style="padding:30px 34px 34px;">
            <p style="margin:0;font-size:15px;line-height:1.7;color:#334150;">
              This email asks you to validate partner-tag recommendations generated for opportunities in your scope.
              Your input is needed to confirm the right partner, correct weak matches, or add context that the model cannot infer from the source data alone.
            </p>

            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:22px;background:#f5f9fc;border:1px solid #dbe8f0;border-radius:16px;">
              <tr>
                <td style="padding:18px 20px;font-size:13px;line-height:1.7;color:#52606d;">
                  <strong style="color:#1d2733;">Why your input matters</strong><br>
                  The browser workspace lets you confirm the best-fit partner, adjust suggestions when needed,
                  and add comments that improve traceability and future recommendations.
                </td>
              </tr>
            </table>

            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:24px;">
              <tr>
                <td align="center">
                  <table cellpadding="0" cellspacing="0" border="0" style="margin:0 auto;">
                    <tr>
                      <td align="center" bgcolor="#1378b5" style="border-radius:999px;background:#1378b5;box-shadow:0 12px 28px rgba(19,120,181,0.22);">
                        <a href="{{ browser_link }}"
                           style="display:inline-block;background:#1378b5;color:#ffffff;text-decoration:none;padding:16px 32px;border-radius:999px;font-size:16px;font-weight:700;letter-spacing:0.01em;border:1px solid #1378b5;">
                          Open Browser Review Workspace
                        </a>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>

            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:24px;background:#f7fafc;border:1px solid #dce6ee;border-radius:16px;">
              <tr>
                <td style="padding:16px 18px;font-size:13px;line-height:1.7;color:#52606d;">
                  <strong style="color:#1d2733;">Why open it in browser?</strong><br>
                  You will see the full review workspace with better rendering, cleaner partner recommendations,
                  and direct action buttons for accept, suggest different, and add comment.
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <tr>
          <td style="padding:18px 32px;border-top:1px solid #e1e4e8;background:#fbfdff;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="font-size:12px;color:#8b949e;">Powered by Capgemini Alliance Team &amp; Invent Switzerland</td>
                <td align="right" style="font-size:12px;color:#8b949e;">{{ now }}</td>
              </tr>
            </table>
          </td>
        </tr>

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
    browser_link: str = "https://outlook.office.com/mail/",
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
            "web_insight": opp.web_insight,
        }
        grouped.setdefault(opp.account_name, []).append(opp_dict)

    total_booking = sum(opp.euro_bkngs for opp in opportunities)

    return template.render(
        grouped=grouped,
        webhook_base=webhook_base,
        lead_name=lead_name or "Sales Lead",
        total_opps=len(opportunities),
        total_opps_word=_num_to_word(len(opportunities)),
        total_booking=total_booking,
      browser_link=browser_link,
        now=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
