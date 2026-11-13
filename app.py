from html import escape as escape_html

import streamlit as st
import pandas as pd
import plotly.express as px
from exact_model import solve_inventory


st.set_page_config(page_title="StockBridge | Transfer Planner", page_icon="📦", layout="wide")

SCENARIOS = {
    "Festival Sale": {
        "budget": 180_000,
        "inventory": [
            {"Product": "Smartphones", "Warehouse": "Kolkata", "Excess": 120, "Shortage": 0, "Priority": 5, "Unit cost": 210},
            {"Product": "Smartphones", "Warehouse": "Bengaluru", "Excess": 0, "Shortage": 95, "Priority": 5, "Unit cost": 210},
            {"Product": "Smartphones", "Warehouse": "Patna", "Excess": 0, "Shortage": 20, "Priority": 4, "Unit cost": 260},
            {"Product": "Refrigerators", "Warehouse": "Kolkata", "Excess": 0, "Shortage": 30, "Priority": 3, "Unit cost": 900},
            {"Product": "Refrigerators", "Warehouse": "Bengaluru", "Excess": 45, "Shortage": 0, "Priority": 3, "Unit cost": 900},
            {"Product": "Grocery packs", "Warehouse": "Kolkata", "Excess": 0, "Shortage": 25, "Priority": 4, "Unit cost": 60},
            {"Product": "Grocery packs", "Warehouse": "Bengaluru", "Excess": 0, "Shortage": 15, "Priority": 3, "Unit cost": 80},
            {"Product": "Grocery packs", "Warehouse": "Patna", "Excess": 70, "Shortage": 0, "Priority": 4, "Unit cost": 60},
        ],
    },
    "Bengaluru Stockout": {
        "budget": 140_000,
        "inventory": [
            {"Product": "Smartphones", "Warehouse": "Kolkata", "Excess": 110, "Shortage": 0, "Priority": 5, "Unit cost": 210},
            {"Product": "Smartphones", "Warehouse": "Bengaluru", "Excess": 0, "Shortage": 105, "Priority": 5, "Unit cost": 210},
            {"Product": "Smartphones", "Warehouse": "Patna", "Excess": 15, "Shortage": 0, "Priority": 2, "Unit cost": 210},
            {"Product": "Refrigerators", "Warehouse": "Kolkata", "Excess": 35, "Shortage": 0, "Priority": 3, "Unit cost": 850},
            {"Product": "Refrigerators", "Warehouse": "Bengaluru", "Excess": 0, "Shortage": 28, "Priority": 4, "Unit cost": 850},
            {"Product": "Grocery packs", "Warehouse": "Kolkata", "Excess": 0, "Shortage": 0, "Priority": 2, "Unit cost": 60},
            {"Product": "Grocery packs", "Warehouse": "Bengaluru", "Excess": 0, "Shortage": 0, "Priority": 2, "Unit cost": 60},
            {"Product": "Grocery packs", "Warehouse": "Patna", "Excess": 40, "Shortage": 0, "Priority": 2, "Unit cost": 60},
        ],
    },
    "Normal Demand": {
        "budget": 100_000,
        "inventory": [
            {"Product": "Smartphones", "Warehouse": "Kolkata", "Excess": 35, "Shortage": 0, "Priority": 4, "Unit cost": 180},
            {"Product": "Smartphones", "Warehouse": "Bengaluru", "Excess": 0, "Shortage": 20, "Priority": 3, "Unit cost": 180},
            {"Product": "Smartphones", "Warehouse": "Patna", "Excess": 0, "Shortage": 5, "Priority": 2, "Unit cost": 230},
            {"Product": "Refrigerators", "Warehouse": "Kolkata", "Excess": 0, "Shortage": 8, "Priority": 2, "Unit cost": 750},
            {"Product": "Refrigerators", "Warehouse": "Bengaluru", "Excess": 14, "Shortage": 0, "Priority": 3, "Unit cost": 750},
            {"Product": "Grocery packs", "Warehouse": "Kolkata", "Excess": 0, "Shortage": 0, "Priority": 2, "Unit cost": 50},
            {"Product": "Grocery packs", "Warehouse": "Bengaluru", "Excess": 10, "Shortage": 0, "Priority": 2, "Unit cost": 50},
            {"Product": "Grocery packs", "Warehouse": "Patna", "Excess": 0, "Shortage": 0, "Priority": 2, "Unit cost": 65},
        ],
    },
}

WAREHOUSES = ["Kolkata", "Bengaluru", "Patna"]


st.markdown("<style>\n.stApp{background:#f6f7f5}.block-container{padding-top:2rem;max-width:1320px}.hero{padding:1.5rem 1.8rem;border-radius:18px;background:linear-gradient(120deg,#143c35,#236b5c);color:#fff;margin-bottom:1.2rem}.hero h1{color:#fff;margin:0;font-size:2.2rem}.hero p{color:#d8ebe4;margin:.4rem 0 0}.smallnote{color:#64716d;font-size:.88rem}.result-table-wrap{overflow-x:auto}.result-table{width:100%;border-collapse:collapse}.result-table th,.result-table td{padding:.65rem .75rem;text-align:left;border-bottom:1px solid #d8dfdb;white-space:nowrap}.result-table th{color:#27483f;background:#eaf0ed}.result-table tbody tr:nth-child(even){background:#f1f5f2}@media(max-width:700px){.block-container{padding:1rem .85rem}.hero{padding:1.2rem}.result-table th,.result-table td{padding:.55rem}}\n</style>", unsafe_allow_html=True)
st.markdown("""
<style>
.position-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr));gap:12px;margin:.4rem 0 1.2rem}
.position-card{background:#fff;border:1px solid #d8dfdb;border-radius:6px;padding:14px 16px;min-width:0}
.position-card h3{font-size:1rem;margin:0 0 8px;color:#23483d}
.position-row{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:8px 0;border-top:1px solid #edf0ee}
.position-product{font-weight:600;min-width:0;overflow-wrap:anywhere}
.position-values{display:flex;justify-content:flex-end;flex-wrap:wrap;gap:5px}
.position-tag{font-size:.78rem;padding:3px 6px;border-radius:3px;white-space:nowrap}
.position-surplus{background:#e6f4ea;color:#17643b}
.position-shortage{background:#fff1dc;color:#8a4b08}
.position-balanced{background:#eef1ef;color:#53615b}
@media(max-width:520px){.position-card{padding:12px}.position-row{align-items:flex-start;flex-direction:column}.position-values{justify-content:flex-start}}
@media(max-width:700px){[data-testid="stHorizontalBlock"]{flex-wrap:wrap!important;gap:.5rem!important}[data-testid="stHorizontalBlock"]>[data-testid="column"]{flex:1 1 calc(50% - .5rem)!important;width:calc(50% - .5rem)!important;min-width:calc(50% - .5rem)!important}}
</style>
""", unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>StockBridge</h1><p>Inventory transfer planner · A Flipkart-inspired classroom prototype</p></div>', unsafe_allow_html=True)
st.caption("Illustrative data only. This prototype uses an exact integer optimization model; it is not Flipkart software or a production optimizer.")

with st.sidebar:
    st.subheader("Planning scenario")
    scenario_name = st.selectbox("Choose a scenario", list(SCENARIOS))
    scenario = SCENARIOS[scenario_name]
    budget = st.number_input("Transfer budget (₹)", min_value=0, value=int(scenario["budget"]), step=10_000)
    st.divider()
    with st.expander("Operating limits", expanded=False):
        out_cap = st.number_input("Outbound limit per warehouse (units)", min_value=1, value=160)
        in_cap = st.number_input("Inbound limit per warehouse (units)", min_value=1, value=140)
        storage_cap = st.number_input("Available storage per destination (units)", min_value=1, value=160)
        truck_cap = st.number_input("Truck capacity (units)", min_value=1, value=100)
        min_fill_pct = st.slider("Minimum truck utilization", min_value=0, max_value=100, value=70, step=5)
        moq = st.number_input("Minimum order quantity (units)", min_value=1, value=10)

st.subheader("Inventory position")
default_df = pd.DataFrame(scenario["inventory"])
edited_rows = []
for product in default_df["Product"].unique():
    product_rows = default_df[default_df["Product"] == product]
    with st.expander(f"{product} · {len(product_rows)} warehouses", expanded=True):
        for row_index, row in product_rows.iterrows():
            with st.container(border=True):
                st.markdown(f"**{row['Warehouse']}**")
                columns = st.columns([1.2, 1, 1, 0.9, 1.2])
                warehouse = columns[0].selectbox(
                    "Warehouse",
                    WAREHOUSES,
                    index=WAREHOUSES.index(row["Warehouse"]),
                    key=f"inventory_{scenario_name}_{row_index}_warehouse",
                )
                excess = columns[1].number_input(
                    "Excess", min_value=0, value=int(row["Excess"]), step=1,
                    key=f"inventory_{scenario_name}_{row_index}_excess",
                )
                shortage = columns[2].number_input(
                    "Shortage", min_value=0, value=int(row["Shortage"]), step=1,
                    key=f"inventory_{scenario_name}_{row_index}_shortage",
                )
                priority = columns[3].number_input(
                    "Priority", min_value=1, max_value=5, value=int(row["Priority"]), step=1,
                    key=f"inventory_{scenario_name}_{row_index}_priority",
                )
                unit_cost = columns[4].number_input(
                    "Unit cost (₹)", min_value=0, value=int(row["Unit cost"]), step=10,
                    key=f"inventory_{scenario_name}_{row_index}_unit_cost",
                )
                edited_rows.append({
                    "Product": row["Product"],
                    "Warehouse": warehouse,
                    "Excess": excess,
                    "Shortage": shortage,
                    "Priority": priority,
                    "Unit cost": unit_cost,
                })
edited = pd.DataFrame(edited_rows, columns=default_df.columns)

st.subheader("Network position")
total_excess = int(edited["Excess"].sum())
total_shortage = int(edited["Shortage"].sum())
transferable_products = set()
for product, product_rows in edited.groupby("Product"):
    sources = product_rows[product_rows["Excess"] > 0]
    destinations = product_rows[product_rows["Shortage"] > 0]
    if any(source.Warehouse != destination.Warehouse for source in sources.itertuples() for destination in destinations.itertuples()):
        transferable_products.add(product)
position_metrics = st.columns(3)
position_metrics[0].metric("Excess inventory", f"{total_excess:,} units")
position_metrics[1].metric("Shortage demand", f"{total_shortage:,} units")
position_metrics[2].metric("Products with a cross-center match", f"{len(transferable_products)} / {edited['Product'].nunique()}")

position_cards = ['<div class="position-cards">']
for warehouse in WAREHOUSES:
    warehouse_rows = edited[edited["Warehouse"] == warehouse]
    position_cards.append(f'<section class="position-card"><h3>{escape_html(warehouse)}</h3>')
    for row in warehouse_rows.itertuples(index=False):
        tags = []
        if row.Excess:
            tags.append(f'<span class="position-tag position-surplus">{int(row.Excess):,} surplus</span>')
        if row.Shortage:
            tags.append(f'<span class="position-tag position-shortage">{int(row.Shortage):,} shortage</span>')
        if not tags:
            tags.append('<span class="position-tag position-balanced">Balanced</span>')
        position_cards.append(
            f'<div class="position-row"><span class="position-product">{escape_html(str(row.Product))}</span>'
            f'<span class="position-values">{"".join(tags)}</span></div>'
        )
    position_cards.append('</section>')
position_cards.append('</div>')
st.markdown("".join(position_cards), unsafe_allow_html=True)

run = st.button("Generate transfer plan", type="primary", width="stretch")
if "plan" not in st.session_state:
    st.session_state.plan = pd.DataFrame()
    st.session_state.remaining = {}
if "unmet_reasons" not in st.session_state:
    st.session_state.unmet_reasons = {}
if run:
    if edited.duplicated(["Product", "Warehouse"]).any():
        st.error("Each product can appear only once at each warehouse. Check the warehouse selections above.")
    elif (edited[["Excess", "Shortage", "Priority", "Unit cost"]] < 0).any().any():
        st.error("Inventory, costs, and priorities must be non-negative.")
    elif (edited["Priority"] > 5).any() or (edited["Priority"] < 1).any():
        st.error("Priority must be between 1 and 5.")
    else:
        st.session_state.plan, st.session_state.remaining, st.session_state.unmet_reasons = solve_inventory(edited, budget, out_cap, in_cap, storage_cap, truck_cap, min_fill_pct / 100, moq)

st.divider()
st.subheader("Recommended transfers")
plan = st.session_state.plan
if plan.empty:
    st.info("Choose or adjust a scenario, then generate a plan. No recommendation is shown until you run the planner.")
else:
    total_units = int(plan["Units"].sum())
    total_cost = int(plan["Transfer cost (₹)"].sum())
    filled = sum(float(r.Shortage) for r in edited.itertuples()) - sum(st.session_state.remaining.values())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Units transferred", f"{total_units:,}")
    c2.metric("Estimated spend", f"₹{total_cost:,}")
    c3.metric("Priority-weighted units", f"{int((plan['Units'] * plan['Priority']).sum()):,}")
    c4.metric("Shortage units filled", f"{max(0, int(filled)):,}")
    display = plan.copy()
    display["Truck fill"] = (display["Truck fill"] * 100).round(0).astype(int).astype(str) + "%"
    st.markdown(
        f'<div class="result-table-wrap">{display.to_html(index=False, escape=True, border=0, classes="result-table")}</div>',
        unsafe_allow_html=True,
    )
    before_after = []
    for r in edited.itertuples():
        before = float(r.Shortage)
        after = st.session_state.remaining.get((r.Product, r.Warehouse), before)
        before_after.extend([{"Product / centre": f"{r.Product} · {r.Warehouse}", "Measure": "Before", "Units": before}, {"Product / centre": f"{r.Product} · {r.Warehouse}", "Measure": "Remaining", "Units": after}])
    chart = px.bar(pd.DataFrame(before_after), x="Units", y="Product / centre", color="Measure", barmode="group", orientation="h", color_discrete_map={"Before": "#a9b8b1", "Remaining": "#237762"}, title="Shortages before and after the recommended transfers")
    chart.update_layout(legend_title_text="", xaxis_title="Units", yaxis_title="", height=max(340, len(before_after) * 32), yaxis={"categoryorder": "total ascending"}, margin={"l": 10, "r": 20, "t": 60, "b": 20})
    st.plotly_chart(chart, width="stretch")
    st.download_button("Download transfer plan (CSV)", plan.to_csv(index=False).encode("utf-8"), file_name="stockbridge_transfer_plan.csv", mime="text/csv")
    with st.expander("About this plan", expanded=False):
        st.markdown("The model first maximizes priority-weighted units fulfilled, then minimizes transfer cost among plans with the best fulfillment score. It enforces stock, shortage, per-warehouse outbound and inbound limits, storage, budget, minimum order quantity, truck capacity, and minimum truck utilization. This is an illustrative optimization model, not a production optimizer.")

unfilled_rows = []
for row in edited.itertuples():
    remaining_units = st.session_state.remaining.get((row.Product, row.Warehouse), 0)
    if remaining_units > 0:
        reasons = st.session_state.unmet_reasons.get((row.Product, row.Warehouse), [])
        unfilled_rows.append({
            "Product": row.Product,
            "Warehouse": row.Warehouse,
            "Unfilled units": int(remaining_units),
            "Why it remains": "; ".join(reasons),
        })
if unfilled_rows:
    st.markdown("**Unfilled demand**")
    unfilled_table = pd.DataFrame(unfilled_rows)
    st.markdown(
        f'<div class="result-table-wrap">{unfilled_table.to_html(index=False, escape=True, border=0, classes="result-table")}</div>',
        unsafe_allow_html=True,
    )

st.divider()
with st.expander("How to present this prototype"):
    st.markdown("1. Select **Festival Sale** and point out a Bengaluru shortage.\n2. Generate the plan and explain which stock moves, its estimated cost, and remaining shortage.\n3. Switch to **Bengaluru Stockout** and compare.\n4. Change the budget or minimum truck utilization to demonstrate a constraint changing the plan.")
