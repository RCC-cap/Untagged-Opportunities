"""Build HTML approval emails for partner tag recommendations."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Template

EMAIL_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Segoe UI, Arial, sans-serif; max-width: 700px; margin: auto;">
  <h2 style="color: #0078d4;">THOR — Partner Tag Recommendation</h2>
  <p>A new partner tag has been suggested for the following opportunity:</p>

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
    <tr>
      <td style="padding: 8px; font-weight: bold;">Recommended Partner</td>
      <td style="padding: 8px; color: #0078d4; font-weight: bold;">{{ primary_partner }}</td>
    </tr>
    {% if secondary_partner %}
    <tr style="background: #f3f3f3;">
      <td style="padding: 8px; font-weight: bold;">Alternative Partner</td>
      <td style="padding: 8px;">{{ secondary_partner }}</td>
    </tr>
    {% endif %}
    <tr>
      <td style="padding: 8px; font-weight: bold;">Confidence</td>
      <td style="padding: 8px;">{{ confidence }}%</td>
    </tr>
    <tr style="background: #f3f3f3;">
      <td style="padding: 8px; font-weight: bold;">Rationale</td>
      <td style="padding: 8px;">{{ rationale }}</td>
    </tr>
  </table>

  <p>Please review and respond:</p>
  <div style="margin: 16px 0;">
    <a href="{{ webhook_base }}/approve?opp_id={{ opp_id }}&partner={{ primary_partner }}"
       style="background: #107c10; color: white; padding: 10px 24px; text-decoration: none; border-radius: 4px; margin-right: 8px;">
      ✅ Accept
    </a>
    <a href="{{ webhook_base }}/reject?opp_id={{ opp_id }}"
       style="background: #d83b01; color: white; padding: 10px 24px; text-decoration: none; border-radius: 4px;">
      ❌ Reject
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
    primary_partner: str,
    confidence: float,
    rationale: str,
    webhook_base: str,
    secondary_partner: str | None = None,
) -> str:
    """Render the approval email HTML."""
    template = Template(EMAIL_TEMPLATE)
    return template.render(
        opp_id=opp_id,
        opp_name=opp_name,
        account_name=account_name,
        primary_partner=primary_partner,
        secondary_partner=secondary_partner,
        confidence=round(confidence, 1),
        rationale=rationale,
        webhook_base=webhook_base,
    )
