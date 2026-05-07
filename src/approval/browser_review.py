"""Browser-first digest review page renderer."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from jinja2 import Template

from src.approval.email_builder import _confidence_badge, _humanize_rationale


REVIEW_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Thor Partner Tagging Agent - {{ lead_name }} - {{ created_at }}</title>
  <link href="https://fonts.googleapis.com/css2?family=Ubuntu:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --blue: #0070ad;
      --blue-soft: #eaf4fb;
      --teal: #12abdb;
      --ink: #1d2733;
      --muted: #5f6b7a;
      --line: #d7dee6;
      --bg: #eff4f8;
      --card: #ffffff;
      --success-bg: #e6f4ea;
      --success-fg: #1e7e34;
      --warn-bg: #fff8e1;
      --warn-fg: #b8860b;
      --danger-bg: #fde7e7;
      --danger-fg: #c62828;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: 'Ubuntu', 'Segoe UI', Arial, sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top right, rgba(18, 171, 219, 0.14), transparent 28%),
        linear-gradient(180deg, #f8fbfd 0%, var(--bg) 100%);
    }
    .shell {
      max-width: 1120px;
      margin: 0 auto;
      padding: 32px 18px 48px;
    }
    .hero {
      background: linear-gradient(135deg, var(--blue) 0%, var(--teal) 100%);
      color: white;
      padding: 28px 30px;
      border-radius: 24px;
      box-shadow: 0 20px 60px rgba(0, 74, 116, 0.18);
    }
    .hero-top {
      display: flex;
      justify-content: space-between;
      gap: 20px;
      align-items: flex-start;
      flex-wrap: wrap;
    }
    .eyebrow {
      font-size: 12px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      opacity: 0.82;
      margin-bottom: 10px;
    }
    h1 {
      margin: 0;
      font-size: 34px;
      line-height: 1.1;
    }
    .hero p {
      margin: 14px 0 0;
      max-width: 760px;
      font-size: 15px;
      line-height: 1.6;
      color: rgba(255,255,255,0.92);
    }
    .stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-top: 22px;
    }
    .stat {
      background: rgba(255,255,255,0.12);
      border: 1px solid rgba(255,255,255,0.16);
      border-radius: 16px;
      padding: 14px 16px;
      backdrop-filter: blur(8px);
    }
    .stat-label {
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      opacity: 0.8;
      margin-bottom: 6px;
    }
    .stat-value {
      font-size: 22px;
      font-weight: 700;
    }
    .section {
      margin-top: 28px;
      background: rgba(255,255,255,0.72);
      border: 1px solid rgba(215, 222, 230, 0.9);
      border-radius: 22px;
      overflow: hidden;
      box-shadow: 0 16px 36px rgba(20, 48, 73, 0.06);
    }
    .section-head {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
      padding: 20px 24px;
      border-bottom: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(255,255,255,0.95), rgba(246,250,252,0.92));
      flex-wrap: wrap;
    }
    .section-title {
      font-size: 18px;
      font-weight: 700;
    }
    .section-meta {
      font-size: 13px;
      color: var(--muted);
    }
    .cards {
      padding: 18px;
      display: grid;
      gap: 16px;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-left: 5px solid var(--blue);
      border-radius: 18px;
      padding: 18px 18px 16px;
    }
    .card-top {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      flex-wrap: wrap;
    }
    .card-title {
      font-size: 19px;
      line-height: 1.25;
      font-weight: 700;
      margin: 0;
    }
    .meta {
      margin-top: 8px;
      font-size: 13px;
      color: var(--muted);
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }
    .badge {
      display: inline-block;
      padding: 6px 12px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
    }
    .badge-row {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }
    .badge-value {
      background: #eaf4fb;
      color: #005b8c;
      border: 1px solid #c7dfef;
    }
    .partner {
      margin-top: 16px;
      font-size: 16px;
      font-weight: 700;
      color: var(--blue);
    }
    .secondary {
      color: var(--muted);
      font-size: 13px;
      font-weight: 500;
      margin-left: 8px;
    }
    .rationale {
      margin-top: 10px;
      font-size: 14px;
      line-height: 1.6;
      color: #334150;
    }
    .web-note {
      margin-top: 8px;
      color: #7a6410;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 16px;
    }
    .button {
      display: inline-block;
      min-height: 44px;
      padding: 11px 16px;
      border-radius: 12px;
      text-decoration: none;
      font-size: 14px;
      font-weight: 700;
      line-height: 20px;
    }
    .button-primary {
      background: linear-gradient(135deg, var(--blue) 0%, var(--teal) 100%);
      color: white;
      box-shadow: 0 10px 24px rgba(0, 112, 173, 0.18);
    }
    .button-secondary {
      background: white;
      color: var(--ink);
      border: 1px solid var(--line);
    }
    .button-tertiary {
      background: transparent;
      color: var(--muted);
      border: 1px dashed var(--line);
    }
    .response {
      margin-top: 14px;
      padding: 12px 14px;
      border-radius: 12px;
      background: #f7fbff;
      border: 1px solid #d6e8f6;
      font-size: 13px;
      line-height: 1.5;
      color: #33506a;
    }
    .footer {
      margin-top: 24px;
      text-align: center;
      font-size: 12px;
      color: var(--muted);
    }
    @media (max-width: 720px) {
      .shell { padding: 18px 12px 28px; }
      .hero { padding: 22px 18px; border-radius: 18px; }
      h1 { font-size: 28px; }
      .section-head { padding: 18px; }
      .cards { padding: 12px; }
      .card { padding: 16px 14px; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="hero-top">
        <div>
          <div class="eyebrow">Thor Partner Tagging Agent</div>
          <h1>Browser Review Workspace</h1>
          <p>You are identified as Opty Lead for {{ total_opps }} opportunit{{ 'y' if total_opps == 1 else 'ies' }} across one or more Capgemini accounts. Review recommendations in a browser-first layout and capture actions with full logging.</p>
        </div>
      </div>
      <div class="stats">
        <div class="stat">
          <div class="stat-label">Opty Lead</div>
          <div class="stat-value">{{ lead_name }}</div>
        </div>
        <div class="stat">
          <div class="stat-label">Opportunities</div>
          <div class="stat-value">{{ total_opps }}</div>
        </div>
        <div class="stat">
          <div class="stat-label">Pipeline Value</div>
          <div class="stat-value">€{{ total_booking }}</div>
        </div>
        <div class="stat">
          <div class="stat-label">Digest Created</div>
          <div class="stat-value">{{ created_at }}</div>
        </div>
        <div class="stat">
          <div class="stat-label">Review ID</div>
          <div class="stat-value">{{ digest_short_id }}</div>
        </div>
      </div>
    </section>

    {% for account_name, account in grouped.items() %}
    <section class="section">
      <div class="section-head">
        <div class="section-title">{{ account_name }}</div>
        <div class="section-meta">{{ account.count }} opportunit{{ 'y' if account.count == 1 else 'ies' }} • €{{ account.total_booking }}</div>
      </div>
      <div class="cards">
        {% for opp in account.opps %}
        <article class="card">
          <div class="card-top">
            <div>
              <h2 class="card-title">{{ opp.opp_name }}</h2>
              <div class="meta">
                {% if opp.stage %}<span>{{ opp.stage }}</span>{% endif %}
                {% if opp.euro_bkngs > 0 %}<span>€{{ opp.euro_bkngs_display }}</span>{% endif %}
                <span>{{ opp.opp_id }}</span>
              </div>
            </div>
            <div class="badge-row">
              {% if opp.euro_bkngs > 0 %}
              <span class="badge badge-value">€{{ opp.euro_bkngs_display }}</span>
              {% endif %}
              <span class="badge" style="background: {{ opp.badge_bg }}; color: {{ opp.badge_fg }};">{{ opp.badge_text }}</span>
            </div>
          </div>

          {% if opp.top_partner %}
          <div class="partner">
            {{ opp.top_partner }}
            {% if opp.secondary %}<span class="secondary">Also: {{ opp.secondary.partner }} ({{ opp.secondary.confidence }}%)</span>{% endif %}
          </div>
          {% endif %}

          {% if opp.web_insight %}<div class="web-note">Thor agent suggestion from public signals</div>{% endif %}

          <div class="rationale">{{ opp.rationale }}</div>

          <div class="actions">
            {% if opp.top_partner %}
            <a class="button button-primary" href="{{ webhook_base }}/select?opp_id={{ opp.opp_id }}&amp;partner={{ opp.top_partner }}&amp;token={{ opp.token }}">Accept{% if opp.show_partner_in_button %} {{ opp.top_partner }}{% endif %}</a>
            {% endif %}
            <a class="button button-secondary" href="{{ webhook_base }}/suggest?opp_id={{ opp.opp_id }}&amp;token={{ opp.token }}">Suggest different</a>
            <a class="button button-tertiary" href="{{ webhook_base }}/comment?opp_id={{ opp.opp_id }}&amp;token={{ opp.token }}">Add comment</a>
          </div>

          {% if opp.response %}
          <div class="response">
            <strong>Recorded response:</strong> {{ opp.response.summary }}
          </div>
          {% endif %}
        </article>
        {% endfor %}
      </div>
    </section>
    {% endfor %}

    <div class="footer">Powered by Capgemini Alliance Team &amp; Invent Switzerland</div>
  </div>
</body>
</html>
"""


def render_review_page(digest: dict[str, Any]) -> str:
    """Render a browser-first review page from a saved digest snapshot."""
    grouped: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for opp in digest["opportunities"]:
        account = grouped.setdefault(
            opp["account_name"],
            {"count": 0, "total_booking": 0.0, "opps": []},
        )
        account["count"] += 1
        account["total_booking"] += float(opp.get("euro_bkngs", 0) or 0)

        candidates = opp.get("candidates", [])
        top = candidates[0] if candidates else None
        has_recommendation = top is not None and top.get("partner") not in {None, "", "Unknown"} and float(top.get("confidence", 0)) > 0

        if opp.get("web_insight"):
          badge_bg, badge_fg = "#fff8e1", "#b8860b"
          top_confidence = float(top.get("confidence", 0)) if top else 0.0
          badge_text = f"AI {round(top_confidence, 1)}%" if top_confidence > 0 else "AI suggestion"
          rationale = opp["web_insight"]
          top_partner = top["partner"] if top else ""
        elif has_recommendation:
            badge_bg, badge_fg = _confidence_badge(float(top["confidence"]))
            badge_text = f"{round(float(top['confidence']), 1)}%"
            rationale = _humanize_rationale(top.get("rationale", ""), top["partner"])
            top_partner = top["partner"]
        else:
            badge_bg, badge_fg = "#fde7e7", "#c62828"
            badge_text = "No match"
            rationale = "No confident internal partner match found. Please suggest the correct partner or add a comment."
            top_partner = ""

        secondary = None
        if len(candidates) > 1:
            second = candidates[1]
            if second.get("partner") not in {None, "", "Unknown"} and float(second.get("confidence", 0)) > 10:
                secondary = {
                    "partner": second["partner"],
                    "confidence": round(float(second["confidence"]), 1),
                }

        response = opp.get("response")
        if response:
            summary = response.get("decision", "responded")
            if response.get("selected_partner"):
                summary = f"{summary}: {response['selected_partner']}"
            elif response.get("comment"):
                summary = f"commented: {response['comment'][:120]}"
            response = {"summary": summary}

        account["opps"].append({
            "opp_id": opp["opp_id"],
            "opp_name": opp["opp_name"],
            "stage": opp.get("stage", ""),
          "euro_bkngs": float(opp.get("euro_bkngs", 0) or 0),
          "euro_bkngs_display": f"{float(opp.get('euro_bkngs', 0) or 0):,.0f}",
            "token": opp["token"],
            "top_partner": top_partner,
            "badge_bg": badge_bg,
            "badge_fg": badge_fg,
            "badge_text": badge_text,
            "rationale": rationale,
            "secondary": secondary,
            "web_insight": opp.get("web_insight", ""),
            "response": response,
            "show_partner_in_button": bool(opp.get("web_insight")),
        })

    template = Template(REVIEW_TEMPLATE)
    return template.render(
        grouped={
            account_name: {
                "count": account["count"],
                "total_booking": f"{account['total_booking']:,.0f}",
                "opps": account["opps"],
            }
            for account_name, account in grouped.items()
        },
        lead_name=digest.get("lead_name", "Sales Lead"),
        total_opps=digest.get("total_opps", len(digest.get("opportunities", []))),
        total_booking=f"{float(digest.get('total_booking', 0) or 0):,.0f}",
        created_at=digest.get("created_at", ""),
        digest_short_id=str(digest.get("digest_id", ""))[:8],
        webhook_base=digest["webhook_base"],
    )