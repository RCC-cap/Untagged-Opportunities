"""Create a small demo Excel file for testing the THOR pipeline."""
import polars as pl
from pathlib import Path

data = {
    "Opportunity Line ID": ["OL-D001", "OL-D002", "OL-D003", "OL-D004"],
    "Opportunity ID": ["OPP-DEMO-001", "OPP-DEMO-002", "OPP-DEMO-003", "OPP-DEMO-004"],
    "Account Name": ["Acme Corp", "Acme Corp", "Acme Corp", "Beta Industries"],
    "Opportunity Name": [
        "Azure Cloud Migration and Modernization",
        "SAP S4HANA Finance Implementation",
        "Cloud Data Platform and Analytics",
        "ERP Modernization Programme",
    ],
    "Euro Bkngs": [50000.0, 80000.0, 35000.0, 120000.0],
    "Weighted Euro Booking": [50000.0, 80000.0, 28000.0, 60000.0],
    "Contribution": [15000.0, 24000.0, 10500.0, 36000.0],
    "Stage": ["Won", "Won", "Open", "Open"],
    "Contract Sign Date": ["2025-12-01", "2025-11-15", None, None],
    "Year": [2025, 2025, 2026, 2026],
    "CM%": [30.0, 30.0, 30.0, 30.0],
    "Offer": ["Cloud Infrastructure", "ERP Implementation", "Data Platform", "ERP Transformation"],
    "Portfolio": ["Cloud Services", "ERP", "Analytics", "ERP"],
    "Selling SBU": ["Cloud AI", "Business Services", "Insights Data", "Business Services"],
    "Selling BU": ["Northern Europe", "Northern Europe", "Northern Europe", "Central Europe"],
    "Selling MU": ["Italy", "Italy", "Italy", "Germany"],
    "Selling MS": ["Milan", "Milan", "Milan", "Munich"],
    "Country": ["Italy", "Italy", "Italy", "Germany"],
    "Partner": ["Microsoft", "SAP", "No Vendor/Partner", "-"],
    "Technology": ["Azure", "SAP S/4HANA", "Azure Synapse", "SAP"],
    "Opp Creation Date": ["2025-10-01", "2025-09-15", "2026-03-01", "2026-02-20"],
    "Sales Stage Date": ["2025-12-01", "2025-11-15", "2026-04-01", "2026-04-10"],
    "Delivery SBU": ["Cloud AI", "Business Services", "Insights Data", "Business Services"],
    "Delivery Unit": ["Cloud Ops", "SAP Practice", "Data Engineering", "SAP Practice"],
    "Business Line L1": ["Technology", "Applications", "Data", "Applications"],
    "Business Line L2": ["Cloud", "ERP", "Analytics", "ERP"],
    "Business Line L3": ["Migration", "Implementation", "Platform", "Modernization"],
    "Sector": ["Financial Services", "Financial Services", "Financial Services", "Manufacturing"],
    "Primary GOU": ["Italy", "Italy", "Italy", "Germany"],
    "Interco Flag": ["N", "N", "N", "N"],
    "Probability%": [100.0, 100.0, 60.0, 50.0],
    "Bid Type": ["Standard", "Standard", "Standard", "Standard"],
    "Opp Type": ["New", "New", "New", "New"],
    "Account Type": ["Strategic", "Strategic", "Strategic", "Key"],
    "Opty Lead": [
        "john.smith@capgemini.com",
        "john.smith@capgemini.com",
        "riccardo-carlo.conte@capgemini.com",
        "riccardo-carlo.conte@capgemini.com",
    ],
}

df = pl.DataFrame(data)
Path("data").mkdir(exist_ok=True)
df.write_excel("data/demo_test.xlsx", worksheet="Sheet1")
untagged = df.filter(pl.col("Partner").is_in(["No Vendor/Partner", "-"]))
print(f"Created data/demo_test.xlsx: {df.height} rows, {untagged.height} untagged")
print(f"Untagged opps assigned to: riccardo-carlo.conte@capgemini.com")
