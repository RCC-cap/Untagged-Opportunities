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
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link href="https://fonts.googleapis.com/css2?family=Ubuntu:wght@300;400;500;700&display=swap" rel="stylesheet">
</head>
<body style="margin: 0; padding: 0; background: #eef1f6; font-family: 'Ubuntu', 'Segoe UI', Roboto, Arial, sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background: #eef1f6; padding: 40px 0;">
    <tr><td align="center">
      <table width="720" cellpadding="0" cellspacing="0" style="background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 8px 32px rgba(0,0,0,0.10);">

        <!-- Logo Bar -->
        <tr><td style="background: #ffffff; padding: 20px 40px; border-bottom: 1px solid #eee;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td>
                <img src="https://www.capgemini.com/wp-content/themes/capgemini2020/assets/images/logo.svg"
                     alt="Capgemini" height="28" style="display: block;" />
              </td>
              <td align="right" style="vertical-align: middle;">
                <span style="display: inline-block; background: #0070AD; color: white; padding: 6px 16px; border-radius: 20px; font-size: 12px; font-weight: 700; font-family: 'Ubuntu', sans-serif; letter-spacing: 0.3px;">&#9889; THOR</span>
              </td>
            </tr>
          </table>
        </td></tr>

        <!-- Header Gradient -->
        <tr><td style="background: linear-gradient(135deg, #0070AD 0%, #12ABDB 60%, #2EDAA8 100%); padding: 36px 40px;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td>
                <p style="margin: 0 0 6px; color: rgba(255,255,255,0.8); font-size: 13px; font-weight: 500; font-family: 'Ubuntu', sans-serif; text-transform: uppercase; letter-spacing: 1px;">Agentic Partner Tagging</p>
                <p style="margin: 0; color: white; font-size: 26px; font-weight: 700; font-family: 'Ubuntu', sans-serif; letter-spacing: -0.3px;">Partner Recommendations</p>
              </td>
              <td align="right" style="vertical-align: bottom;">
                <span style="display: inline-block; background: rgba(255,255,255,0.18); color: white; padding: 7px 18px; border-radius: 20px; font-size: 12px; font-weight: 600; font-family: 'Ubuntu', sans-serif;">&#128197; Daily Digest</span>
              </td>
            </tr>
          </table>
        </td></tr>

        <!-- Greeting & Introduction -->
        <tr><td style="padding: 32px 40px 12px;">
          <p style="margin: 0 0 18px; color: #1a1a1a; font-size: 18px; font-weight: 500; font-family: 'Ubuntu', sans-serif; line-height: 1.4;">
            Dear {{ lead_name }},
          </p>
          <p style="margin: 0 0 16px; color: #444; font-size: 15px; line-height: 1.8; font-family: 'Ubuntu', sans-serif;">
            You have untagged opportunities in your pipeline that are missing a partner attribution.
            <strong style="color: #0070AD;">Accurate partner tagging is critical</strong> for our business &mdash;
            it drives correct revenue recognition, enables strategic alliance reporting to leadership,
            and ensures our hyperscaler &amp; partner investments are properly measured.
          </p>
          <p style="margin: 0 0 16px; color: #444; font-size: 15px; line-height: 1.8; font-family: 'Ubuntu', sans-serif;">
            THOR has analysed your opportunities using <strong>keyword matching</strong>, <strong>account history</strong>,
            <strong>technology signals</strong>, and our <strong>partner taxonomy</strong> to recommend the best-fit partner.
          </p>
        </td></tr>

        <!-- Action Required Box -->
        <tr><td style="padding: 0 40px 24px;">
          <table width="100%" cellpadding="0" cellspacing="0" style="background: #EBF5FF; border-radius: 12px; border-left: 5px solid #0070AD; overflow: hidden;">
            <tr><td style="padding: 18px 24px;">
              <p style="margin: 0; color: #0070AD; font-size: 15px; font-weight: 700; font-family: 'Ubuntu', sans-serif;">
                &#9997;&#65039; Action required
              </p>
              <p style="margin: 8px 0 0; color: #333; font-size: 14px; line-height: 1.7; font-family: 'Ubuntu', sans-serif;">
                Review each opportunity below. Click <strong>"Select"</strong> to confirm the recommended partner,
                or <strong>"Reject All"</strong> if none of the suggestions apply. Your feedback improves future recommendations.
              </p>
            </td></tr>
          </table>
        </td></tr>

        <!-- Summary bar -->
        <tr><td style="padding: 0 40px 20px;">
          <table width="100%" cellpadding="0" cellspacing="0" style="background: linear-gradient(135deg, #0070AD 0%, #12ABDB 100%); border-radius: 12px; overflow: hidden;">
            <tr>
              <td style="padding: 18px 24px;">
                <table width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td style="font-size: 15px; color: white; font-weight: 600; font-family: 'Ubuntu', sans-serif;">
                      &#128202; {{ opportunities|length }} opportunit{{ 'y' if opportunities|length == 1 else 'ies' }} awaiting review
                    </td>
                    <td align="right" style="font-size: 15px; color: white; font-weight: 700; font-family: 'Ubuntu', sans-serif;">
                      {% set total_value = opportunities|sum(attribute='euro_bkngs') %}
                      {% if total_value > 0 %}&euro;{{ "{:,.0f}".format(total_value) }} pipeline value{% endif %}
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
        </td></tr>

        <!-- Confidence legend -->
        <tr><td style="padding: 0 40px 20px;">
          <table width="100%" cellpadding="0" cellspacing="0" style="background: #f9fafb; border-radius: 10px; border: 1px solid #e8eaed;">
            <tr><td style="padding: 14px 20px;">
              <table cellpadding="0" cellspacing="0" style="font-size: 13px; color: #666; font-family: 'Ubuntu', sans-serif;">
                <tr>
                  <td style="padding-right: 8px; font-weight: 700; color: #333;">&#128308; Confidence:</td>
                  <td style="padding-right: 20px;"><span style="display: inline-block; background: #e6f4ea; color: #1e7e34; padding: 3px 10px; border-radius: 12px; font-weight: 700; font-size: 12px;">&ge;80%</span> High</td>
                  <td style="padding-right: 20px;"><span style="display: inline-block; background: #fff8e1; color: #b8860b; padding: 3px 10px; border-radius: 12px; font-weight: 700; font-size: 12px;">50-79%</span> Medium</td>
                  <td style="padding-right: 20px;"><span style="display: inline-block; background: #fff3e0; color: #e65100; padding: 3px 10px; border-radius: 12px; font-weight: 700; font-size: 12px;">30-49%</span> Low</td>
                  <td><span style="display: inline-block; background: #fde7e7; color: #c62828; padding: 3px 10px; border-radius: 12px; font-weight: 700; font-size: 12px;">&lt;30%</span> Uncertain</td>
                </tr>
              </table>
            </td></tr>
          </table>
        </td></tr>

        {% for opp in opportunities %}
        <!-- Opportunity Card -->
        <tr><td style="padding: 8px 40px 20px;">
          <table width="100%" cellpadding="0" cellspacing="0" style="border: 2px solid #e0e3e8; border-radius: 14px; overflow: hidden;">

            <!-- Card header -->
            <tr><td style="background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%); padding: 20px 24px; border-bottom: 2px solid #e8eaed;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="font-size: 18px; font-weight: 700; color: #1a1a1a; font-family: 'Ubuntu', sans-serif;">{{ opp.opp_name }}</td>
                  {% if opp.euro_bkngs > 0 %}
                  <td align="right" style="font-size: 17px; font-weight: 700; color: #0070AD; font-family: 'Ubuntu', sans-serif;">&euro;{{ "{:,.0f}".format(opp.euro_bkngs) }}</td>
                  {% endif %}
                </tr>
              </table>
            </td></tr>

            <!-- Card meta -->
            <tr><td style="padding: 16px 24px 12px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="font-size: 13px; color: #666; font-family: 'Ubuntu', sans-serif;">
                <tr>
                  <td style="padding: 4px 0;"><span style="color: #999;">&#128196; ID:</span> <strong style="color: #333;">{{ opp.opp_id }}</strong></td>
                  <td style="padding: 4px 0;"><span style="color: #999;">&#127970; Account:</span> <strong style="color: #333;">{{ opp.account_name }}</strong></td>
                  {% if opp.stage %}<td style="padding: 4px 0;"><span style="color: #999;">&#128640; Stage:</span> <strong style="color: #333;">{{ opp.stage }}</strong></td>{% endif %}
                </tr>
              </table>
            </td></tr>

            <!-- Candidates -->
            {% for candidate in opp.candidates %}
            <tr><td style="padding: 6px 24px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="border: {% if loop.first %}2px solid #0070AD{% else %}1px solid #e0e0e0{% endif %}; border-radius: 12px; overflow: hidden; {% if loop.first %}box-shadow: 0 2px 8px rgba(0,112,173,0.12);{% endif %}">
                <tr>
                  <td style="background: {% if loop.first %}linear-gradient(135deg, #0070AD 0%, #12ABDB 100%){% else %}#f8f9fb{% endif %}; padding: 14px 20px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="color: {% if loop.first %}white{% else %}#333{% endif %}; font-size: 16px; font-weight: 700; font-family: 'Ubuntu', sans-serif;">
                          {% if loop.first %}&#11088; Recommended: {% else %}&#128313; Alternative: {% endif %}{{ candidate.partner }}
                        </td>
                        <td align="right">
                          <span style="display: inline-block; background: {% if loop.first %}rgba(255,255,255,0.25){% else %}{{ candidate.badge_bg }}{% endif %}; color: {% if loop.first %}white{% else %}{{ candidate.badge_fg }}{% endif %}; padding: 4px 14px; border-radius: 14px; font-size: 13px; font-weight: 700; font-family: 'Ubuntu', sans-serif;">
                            {{ candidate.confidence }}%
                          </span>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr>
                  <td style="padding: 16px 20px; background: white;">
                    <p style="margin: 0 0 6px; font-size: 12px; font-weight: 700; color: #0070AD; text-transform: uppercase; letter-spacing: 0.5px; font-family: 'Ubuntu', sans-serif;">&#128269; Why this partner?</p>
                    <p style="margin: 0 0 16px; font-size: 14px; color: #444; line-height: 1.7; font-family: 'Ubuntu', sans-serif;">{{ candidate.rationale }}</p>
                    <a href="{{ webhook_base }}/select?opp_id={{ opp.opp_id }}&partner={{ candidate.partner }}&token={{ opp.token }}"
                       style="display: inline-block; background: {% if loop.first %}linear-gradient(135deg, #0070AD 0%, #12ABDB 100%){% else %}#f4f5f7{% endif %}; color: {% if loop.first %}white{% else %}#333{% endif %}; padding: 12px 32px; text-decoration: none; border-radius: 8px; font-size: 14px; font-weight: 700; font-family: 'Ubuntu', sans-serif; {% if not loop.first %}border: 2px solid #ddd;{% endif %}">
                      &#10004; Select {{ candidate.partner }}
                    </a>
                  </td>
                </tr>
              </table>
            </td></tr>
            {% endfor %}

            <!-- Reject -->
            <tr><td style="padding: 16px 24px 22px;">
              <a href="{{ webhook_base }}/reject?opp_id={{ opp.opp_id }}&token={{ opp.token }}"
                 style="display: inline-block; background: #FFF0ED; color: #d83b01; padding: 11px 28px; text-decoration: none; border-radius: 8px; font-size: 13px; font-weight: 700; border: 2px solid #FECDC8; font-family: 'Ubuntu', sans-serif;">
                &#10060; Reject All Suggestions
              </a>
              <span style="display: inline-block; padding-left: 14px; font-size: 12px; color: #999; vertical-align: middle; font-family: 'Ubuntu', sans-serif;">No partner applies</span>
            </td></tr>

          </table>
        </td></tr>
        {% endfor %}

        <!-- How it works -->
        <tr><td style="padding: 8px 40px 24px;">
          <table width="100%" cellpadding="0" cellspacing="0" style="background: linear-gradient(180deg, #f0f7ff 0%, #f8fbff 100%); border-radius: 12px; border: 1px solid #d4e5f7;">
            <tr><td style="padding: 20px 24px;">
              <p style="margin: 0 0 10px; font-size: 14px; font-weight: 700; color: #0070AD; font-family: 'Ubuntu', sans-serif;">&#129302; How does THOR generate recommendations?</p>
              <table cellpadding="0" cellspacing="0" style="font-size: 13px; color: #555; line-height: 1.8; font-family: 'Ubuntu', sans-serif;">
                <tr><td style="padding: 3px 0;">&#128273; <strong>Keyword extraction</strong> &mdash; Analyses opportunity name, offer, and technology fields</td></tr>
                <tr><td style="padding: 3px 0;">&#128200; <strong>Account history</strong> &mdash; Looks at previously tagged opportunities for the same account to identify established partner relationships</td></tr>
                <tr><td style="padding: 3px 0;">&#127959; <strong>Taxonomy mapping</strong> &mdash; Matches against Capgemini&rsquo;s official partner portfolio and technology domains</td></tr>
                <tr><td style="padding: 3px 0;">&#127942; <strong>Strategic weighting</strong> &mdash; Tier-1 hyperscalers (Microsoft, AWS, Google, SAP, Oracle) receive a priority boost</td></tr>
              </table>
              <p style="margin: 12px 0 0; font-size: 12px; color: #888; font-family: 'Ubuntu', sans-serif;">
                The confidence % reflects the combined signal strength from all scoring factors.
              </p>
            </td></tr>
          </table>
        </td></tr>

        <!-- Footer -->
        <tr><td style="background: #1a2332; padding: 28px 40px; border-top: none;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td>
                <p style="margin: 0 0 4px; font-size: 13px; color: rgba(255,255,255,0.9); font-weight: 600; font-family: 'Ubuntu', sans-serif;">
                  THOR &mdash; Agentic Partner Tagging
                </p>
                <p style="margin: 0; font-size: 12px; color: rgba(255,255,255,0.5); font-family: 'Ubuntu', sans-serif;">
                  Capgemini Switzerland &bull; Technology &amp; Innovation
                </p>
              </td>
              <td align="right" style="vertical-align: bottom;">
                <p style="margin: 0; font-size: 11px; color: rgba(255,255,255,0.4); font-family: 'Ubuntu', sans-serif;">{{ now }}</p>
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
        lead_name=lead_name or "Sales Lead",
        now=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
