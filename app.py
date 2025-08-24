# app.py
# Mortgage Outcomes — modern web UI with Streamlit
# Calculates equity above down payment for years 1–10 across sale-price options.

import math
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np
import pandas as pd
import streamlit as st

# ---------- Core math ----------
def monthly_payment(principal: float, apr: float, years: int) -> float:
    r = apr / 12.0
    n = years * 12
    if r == 0:
        return principal / n
    return principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)

def remaining_balance(principal: float, apr: float, years_total: int, years_paid: int) -> float:
    r = apr / 12.0
    n_total = years_total * 12
    n_paid = years_paid * 12
    if r == 0:
        return principal * (1 - n_paid / n_total)
    return principal * ((1 + r) ** n_total - (1 + r) ** n_paid) / ((1 + r) ** n_total - 1)

def equity_above_down_payment(
    purchase_price: float,
    down_payment_amount: float,
    apr: float,
    term_years: int,
    sale_price: float,
    year: int,
    fees_pct: float,
    fees_flat: float,
    service_charge_per_year: float = 0.0,
) -> Tuple[float, float, float, float]:
    """Returns (emi, rem_balance, net_after_costs, equity_above_dp)."""
    loan = purchase_price - down_payment_amount
    emi = monthly_payment(loan, apr, term_years)
    rem = remaining_balance(loan, apr, term_years, year)
    net_before_costs = sale_price - rem
    total_fees = sale_price * fees_pct + fees_flat
    total_service = service_charge_per_year * year
    net_after_costs = net_before_costs - total_fees - total_service
    above_dp = net_after_costs - down_payment_amount
    return emi, rem, net_after_costs, above_dp

# ---------- UI ----------
st.set_page_config(page_title="Mortgage Outcomes", page_icon="📈", layout="wide")

st.title("📈 Mortgage Outcomes Calculator")
st.caption("Modern UI • Instant results • Downloadable CSV")

with st.sidebar:
    st.subheader("Setup")
    colA, colB = st.columns(2)
    with colA:
        currency = st.selectbox("Currency", ["AED", "USD", "EUR"], index=0)
    with colB:
        dec = st.number_input("Round to (0=whole)", min_value=0, max_value=2, value=0, step=1)

    st.markdown("---")
    st.subheader("Purchase & Loan")
    purchase_price = st.number_input("Purchase Price", min_value=0.0, value=3_150_000.0, step=10_000.0, format="%.2f")
    dp_mode = st.radio("Down Payment Mode", ["Percent", "Amount"], horizontal=True)
    if dp_mode == "Percent":
        dp_pct = st.number_input("Down Payment %", min_value=0.0, max_value=100.0, value=20.0, step=1.0) / 100.0
        down_payment = purchase_price * dp_pct
    else:
        down_payment = st.number_input("Down Payment Amount", min_value=0.0, value=630_000.0, step=10_000.0, format="%.2f")
        dp_pct = down_payment / purchase_price if purchase_price else 0.0

    apr = st.number_input("Interest Rate (APR %)", min_value=0.0, max_value=50.0, value=4.74, step=0.01) / 100.0
    term_years = st.number_input("Term (years)", min_value=1, max_value=40, value=20, step=1)

    st.markdown("---")
    st.subheader("Sale & Costs")
    resale_prices_str = st.text_input("Resale Price Options (comma-separated)",
                                      value="2500000,3000000,3150000")
    resale_prices = []
    for x in resale_prices_str.split(","):
        x = x.strip().replace(",", "")
        if x:
            try:
                resale_prices.append(float(x))
            except ValueError:
                pass

    fees_pct = st.number_input("Commission / Fees (% of sale)", min_value=0.0, max_value=20.0, value=4.0, step=0.25) / 100.0
    fees_flat = st.number_input("Flat Fee Amount", min_value=0.0, value=0.0, step=1_000.0, format="%.2f")
    service_charge_per_year = st.number_input("Service Charge per Year", min_value=0.0, value=0.0, step=1_000.0, format="%.2f")

    st.markdown("---")
    st.subheader("Horizon")
    years_max = st.slider("Show years 1…N", min_value=1, max_value=30, value=10, step=1)

# Header cards
loan_amount = max(purchase_price - down_payment, 0.0)
emi_preview = monthly_payment(loan_amount, apr, term_years) if loan_amount else 0.0

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Purchase Price", f"{purchase_price:,.0f} {currency}")
m2.metric("Down Payment", f"{down_payment:,.0f} {currency}", f"{dp_pct*100:.1f}%")
m3.metric("Loan Amount", f"{loan_amount:,.0f} {currency}")
m4.metric("APR", f"{apr*100:.2f}%")
m5.metric("Monthly Payment", f"{emi_preview:,.0f} {currency}")

st.markdown("### Results")
if not resale_prices:
    st.info("Add at least one resale price to see results.")
    st.stop()

years = list(range(1, years_max + 1))
table_rows = []
for y in years:
    row = {"Year": y}
    for sp in resale_prices:
        _, _, _, above = equity_above_down_payment(
            purchase_price, down_payment, apr, term_years,
            sp, y, fees_pct, fees_flat, service_charge_per_year
        )
        if dec == 0:
            row[f"Sale {sp:,.0f}"] = round(above)
        else:
            row[f"Sale {sp:,.0f}"] = round(above, dec)
    table_rows.append(row)

df = pd.DataFrame(table_rows)

# Pretty table
st.dataframe(df.style.format({c: "{:,.0f}".format for c in df.columns if c != "Year"}), use_container_width=True)

# Chart
st.markdown("#### Equity Above Down Payment Over Time")
chart_df = df.set_index("Year")
st.line_chart(chart_df)

# Download
csv = df.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Download CSV", csv, file_name="mortgage_outcomes.csv", mime="text/csv")

st.caption("Formulae: standard EMI; remaining balance after n payments; equity above DP = net proceeds after fees & service charges minus down payment.")
