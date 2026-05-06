"""Generate a realistic 1000-opportunity demo dataset.

- 100 clients, 10 opps each, spread across 2021-2026
- ~78% tagged (with realistic partner distribution), ~22% untagged
- Matches VBA 1.xlsm column structure exactly
- Opty Lead = riccardo-carlo.conte@capgemini.com
"""

import random
from datetime import date, timedelta
from pathlib import Path

import polars as pl

random.seed(42)

# ──────────────────────────────────────────────────────────────────────────────
# Reference data
# ──────────────────────────────────────────────────────────────────────────────

ACCOUNTS = [
    "Acme Corp", "Beta Industries", "Gamma Technologies", "Delta Financial",
    "Epsilon Pharma", "Zeta Energy", "Eta Logistics", "Theta Retail",
    "Iota Telecom", "Kappa Insurance", "Lambda Motors", "Mu Healthcare",
    "Nu Media", "Xi Manufacturing", "Omicron Banking", "Pi Aerospace",
    "Rho Chemicals", "Sigma Defence", "Tau Utilities", "Upsilon Foods",
    "Phi Construction", "Chi Electronics", "Psi Transport", "Omega Mining",
    "Alpha Shipping", "Bravo Aviation", "Charlie Biotech", "Delta Robotics",
    "Echo Automotive", "Foxtrot Payments", "Golf Renewables", "Hotel Hospitality",
    "India Semiconductor", "Juliet Fashion", "Kilo Agriculture", "Lima Rail",
    "Mike Petrochemicals", "November Telehealth", "Oscar Fintech", "Papa Logistics",
    "Quebec Steel", "Romeo Water", "Sierra Cloud", "Tango Digital",
    "Uniform Pharma", "Victor Materials", "Whiskey Textiles", "Xray Diagnostics",
    "Yankee Space", "Zulu Marine", "Ares Consulting", "Apollo Solar",
    "Athena Analytics", "Hermes Express", "Poseidon Offshore", "Demeter Agri",
    "Hephaestus Forge", "Artemis Health", "Dionysus Spirits", "Hera Cosmetics",
    "Prometheus AI", "Titan Engineering", "Orion Optics", "Pegasus Airlines",
    "Phoenix Recycling", "Sphinx Security", "Triton Subsea", "Centaur Biopharma",
    "Griffin Aviation", "Hydra Networks", "Minotaur Metals", "Cerberus Cyber",
    "Chimera Ventures", "Medusa Chemicals", "Kraken Maritime", "Valkyrie Defence",
    "Thor Power", "Odin Consulting", "Freya Retail Tech", "Loki Games",
    "Baldur Optics", "Fenrir Logistics", "Mjolnir Heavy", "Ragnarok Energy",
    "Yggdrasil Forest", "Asgard Telecom", "Midgard Industries", "Bifrost Networks",
    "Valhalla Mining", "Norns Analytics", "Jotun Cooling", "Alfheim Solar",
    "Svartalfheim Mining", "Niflheim Cryo", "Muspelheim Thermal", "Helheim Waste",
    "Vanir Agriculture", "Einherjar Security", "Sleipnir Transport", "Gungnir Precision",
]

PARTNERS = {
    "Microsoft": 0.25,
    "SAP": 0.15,
    "AWS": 0.12,
    "Oracle": 0.08,
    "Google": 0.06,
    "Salesforce": 0.05,
    "ServiceNow": 0.04,
    "IBM": 0.03,
}

# 22% untagged
UNTAGGED_RATE = 0.22

# Partner-specific offers/technologies for realistic clustering
PARTNER_PROFILES = {
    "Microsoft": {
        "offers": ["Cloud Migration", "Azure Infrastructure", "Modern Workplace", "Dynamics 365", "Power Platform", "Security & Compliance", "Data & AI Platform"],
        "technologies": ["Azure", "Microsoft 365", "Dynamics 365", "Power BI", "Azure AI", "Azure DevOps", "Copilot"],
        "portfolios": ["Cloud", "Digital Workplace", "Business Applications", "Cybersecurity", "Data & AI"],
    },
    "SAP": {
        "offers": ["S/4HANA Migration", "SAP ERP Implementation", "SAP Analytics", "SAP Integration", "SAP BTP Development", "SAP SuccessFactors"],
        "technologies": ["SAP S/4HANA", "SAP BW/4HANA", "SAP BTP", "SAP Fiori", "SAP SuccessFactors", "SAP Ariba"],
        "portfolios": ["ERP", "Business Applications", "Analytics", "Supply Chain"],
    },
    "AWS": {
        "offers": ["AWS Migration", "Cloud Native Development", "AWS Data Lake", "AWS Managed Services", "Serverless Architecture"],
        "technologies": ["AWS", "Amazon EKS", "AWS Lambda", "Amazon Redshift", "AWS SageMaker", "Amazon S3"],
        "portfolios": ["Cloud", "Data & AI", "DevOps", "Infrastructure"],
    },
    "Oracle": {
        "offers": ["Oracle Cloud Migration", "Oracle ERP Implementation", "Database Modernization", "Oracle HCM"],
        "technologies": ["Oracle Cloud", "Oracle EBS", "Oracle DB", "Oracle Fusion", "Oracle HCM Cloud"],
        "portfolios": ["ERP", "Cloud", "Database", "Business Applications"],
    },
    "Google": {
        "offers": ["Google Cloud Platform", "BigQuery Analytics", "Google Workspace", "Anthos Hybrid Cloud", "Vertex AI"],
        "technologies": ["GCP", "BigQuery", "Google Workspace", "Anthos", "Vertex AI", "Looker"],
        "portfolios": ["Cloud", "Data & AI", "Digital Workplace", "Analytics"],
    },
    "Salesforce": {
        "offers": ["Salesforce CRM Implementation", "Marketing Cloud", "Service Cloud", "MuleSoft Integration"],
        "technologies": ["Salesforce", "MuleSoft", "Tableau", "Marketing Cloud", "Service Cloud"],
        "portfolios": ["CRM", "Marketing", "Integration", "Customer Experience"],
    },
    "ServiceNow": {
        "offers": ["ITSM Implementation", "ServiceNow Platform", "IT Operations Management", "HR Service Delivery"],
        "technologies": ["ServiceNow", "ITSM", "ITOM", "CSM", "HRSD"],
        "portfolios": ["IT Service Management", "Operations", "Employee Experience"],
    },
    "IBM": {
        "offers": ["IBM Cloud Migration", "Mainframe Modernization", "IBM watsonx", "Red Hat OpenShift"],
        "technologies": ["IBM Cloud", "IBM Z", "Red Hat", "watsonx", "OpenShift"],
        "portfolios": ["Cloud", "Infrastructure Modernization", "AI", "Hybrid Cloud"],
    },
}

# Generic offers/techs for untagged opps (ambiguous - could be any partner)
GENERIC_OFFERS = [
    "Digital Transformation", "IT Strategy", "Application Modernization",
    "Cloud Strategy Assessment", "Data Analytics", "Cybersecurity Assessment",
    "Process Automation", "AI Strategy", "Infrastructure Optimization",
    "Customer Experience Transformation", "Supply Chain Optimization",
    "Managed Services", "Testing & QA", "DevOps Transformation",
]

GENERIC_TECHNOLOGIES = [
    "Multiple", "TBD", "Cloud", "AI/ML", "IoT", "Blockchain",
    "RPA", "Low-Code", "Microservices", "Containers", "API Management",
    "Data Integration", "Machine Learning", "Generative AI",
]

STAGES = ["Qualify", "Develop", "Propose", "Negotiate", "Won", "Lost"]
STAGE_WEIGHTS = [0.15, 0.20, 0.25, 0.20, 0.12, 0.08]

COUNTRIES = ["France", "Germany", "UK", "Italy", "Spain", "Netherlands", "Sweden", "Switzerland", "Belgium", "Norway"]

SELLING_SBUS = ["Cloud Infrastructure Services", "Application Services", "Business Services", "Insights & Data", "Digital Engineering", "Intelligent Industry"]
SELLING_BUS = ["Northern Europe", "Central Europe", "Southern Europe", "France", "UK&I"]
SELLING_MUS = ["France MU", "Germany MU", "UK MU", "Italy MU", "Nordics MU", "Benelux MU"]
SELLING_MSS = ["Paris", "Munich", "London", "Milan", "Stockholm", "Amsterdam", "Zurich", "Madrid"]

DELIVERY_SBUS = ["CIS", "Apps", "Business Services", "I&D", "Digital Engineering"]
DELIVERY_UNITS = ["Delivery Unit France", "Delivery Unit India", "Delivery Unit Poland", "Delivery Unit Spain", "Nearshore Hub"]

BL_L1 = ["Technology", "Strategy", "Operations", "Engineering"]
BL_L2 = ["Cloud", "Enterprise Apps", "Digital", "Analytics", "Security", "Infrastructure"]
BL_L3 = ["Migration", "Implementation", "Managed Services", "Consulting", "Development", "Integration"]

SECTORS = ["Financial Services", "Manufacturing", "Public Sector", "Energy & Utilities", "Telecom", "Healthcare", "Retail", "Automotive", "Aerospace & Defence"]

ACCOUNT_TYPES = ["Strategic", "Key", "Named", "Territory"]
BID_TYPES = ["Competitive", "Sole Source", "Extension", "Framework"]
OPP_TYPES = ["New", "Extension", "Renewal", "Cross-sell", "Up-sell"]

OPTY_LEAD = "riccardo-carlo.conte@capgemini.com"


def random_date(start_year: int, end_year: int) -> date:
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def generate_opp_name(partner: str | None, offer: str) -> str:
    """Generate a realistic opportunity name."""
    prefixes = ["", "Phase 2 - ", "Programme - ", ""]
    suffixes = ["", " - Year 2", " Extension", " Rollout", ""]
    return f"{random.choice(prefixes)}{offer}{random.choice(suffixes)}".strip(" -")


def main():
    rows = []
    opp_counter = 1

    # Assign each account a "primary partner tendency" (accounts tend to cluster)
    account_partner_affinity = {}
    partners_list = list(PARTNERS.keys())
    for account in ACCOUNTS:
        # Each account has 1-2 primary partners they work with most
        primary = random.choice(partners_list)
        secondary = random.choice([p for p in partners_list if p != primary])
        account_partner_affinity[account] = (primary, secondary)

    for account in ACCOUNTS:
        primary_partner, secondary_partner = account_partner_affinity[account]
        country = random.choice(COUNTRIES)
        sector = random.choice(SECTORS)
        account_type = random.choice(ACCOUNT_TYPES)

        for opp_idx in range(10):
            opp_id = f"OPP-{opp_counter:05d}"
            line_id = f"LN-{opp_counter:05d}-01"
            opp_counter += 1

            # Decide if this opp is tagged or untagged
            is_untagged = random.random() < UNTAGGED_RATE

            if is_untagged:
                partner_tag = random.choice(["No Vendor/Partner", "-"])
                # Use generic (ambiguous) offers/techs
                offer = random.choice(GENERIC_OFFERS)
                technology = random.choice(GENERIC_TECHNOLOGIES)
                portfolio = random.choice(["Cloud", "Digital", "Analytics", "Enterprise Apps", "Consulting"])
            else:
                # Pick partner with affinity bias
                r = random.random()
                if r < 0.50:
                    partner_tag = primary_partner
                elif r < 0.75:
                    partner_tag = secondary_partner
                else:
                    partner_tag = random.choices(partners_list, weights=[PARTNERS[p] for p in partners_list])[0]

                profile = PARTNER_PROFILES[partner_tag]
                offer = random.choice(profile["offers"])
                technology = random.choice(profile["technologies"])
                portfolio = random.choice(profile["portfolios"])

            # Timing across 5 years
            creation_date = random_date(2021, 2026)
            stage = random.choices(STAGES, weights=STAGE_WEIGHTS)[0]
            sales_stage_date = creation_date + timedelta(days=random.randint(7, 180))

            # Contract sign date only for Won
            contract_sign_date = None
            if stage == "Won":
                contract_sign_date = sales_stage_date + timedelta(days=random.randint(1, 60))

            year = creation_date.year

            # Financials
            euro_bkngs = round(random.uniform(10_000, 5_000_000), 2)
            probability = {"Qualify": 10, "Develop": 25, "Propose": 50, "Negotiate": 75, "Won": 100, "Lost": 0}[stage]
            weighted = round(euro_bkngs * probability / 100, 2)
            contribution = round(euro_bkngs * random.uniform(0.15, 0.45), 2)
            cm_pct = round(random.uniform(10, 50), 1)

            opp_name = generate_opp_name(partner_tag if not is_untagged else None, offer)

            rows.append({
                "Opportunity Line ID": line_id,
                "Opportunity ID": opp_id,
                "Account Name": account,
                "Opportunity Name": opp_name,
                "Euro Bkngs": euro_bkngs,
                "Weighted Euro Booking": weighted,
                "Contribution": contribution,
                "Stage": stage,
                "Contract Sign Date": contract_sign_date,
                "Year": year,
                "CM%": cm_pct,
                "Offer": offer,
                "Portfolio": portfolio,
                "Selling SBU": random.choice(SELLING_SBUS),
                "Selling BU": random.choice(SELLING_BUS),
                "Selling MU": random.choice(SELLING_MUS),
                "Selling MS": random.choice(SELLING_MSS),
                "Country": country,
                "Partner": partner_tag,
                "Technology": technology,
                "Opp Creation Date": creation_date,
                "Sales Stage Date": sales_stage_date,
                "Delivery SBU": random.choice(DELIVERY_SBUS),
                "Delivery Unit": random.choice(DELIVERY_UNITS),
                "Business Line L1": random.choice(BL_L1),
                "Business Line L2": random.choice(BL_L2),
                "Business Line L3": random.choice(BL_L3),
                "Sector": sector,
                "Primary GOU": random.choice(["GOU-" + c[:3].upper() for c in COUNTRIES]),
                "Interco Flag": random.choice(["Y", "N", "N", "N"]),
                "Probability%": probability,
                "Bid Type": random.choice(BID_TYPES),
                "Opp Type": random.choice(OPP_TYPES),
                "Account Type": account_type,
                "Opty Lead": OPTY_LEAD,
            })

    df = pl.DataFrame(rows)

    # Summary
    total = df.height
    untagged = df.filter(pl.col("Partner").is_in(["No Vendor/Partner", "-"])).height
    tagged = total - untagged
    print(f"Generated {total} opportunities:")
    print(f"  Tagged: {tagged} ({tagged/total*100:.0f}%)")
    print(f"  Untagged: {untagged} ({untagged/total*100:.0f}%)")
    print(f"  Accounts: {df['Account Name'].n_unique()}")
    print(f"  Date range: {df['Opp Creation Date'].min()} to {df['Opp Creation Date'].max()}")
    print()
    print("Partner distribution (tagged only):")
    print(
        df.filter(~pl.col("Partner").is_in(["No Vendor/Partner", "-"]))
        .group_by("Partner")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
    )

    # Write to Excel
    out_path = Path("data/demo_1000.xlsx")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_excel(out_path)
    print(f"\nSaved to: {out_path}")


if __name__ == "__main__":
    main()
