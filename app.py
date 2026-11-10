import streamlit as st
import pandas as pd
import plotly.express as px


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


def recommend_transfers(inventory, budget, out_cap, in_cap, storage_cap, truck_cap, min_fill, moq):
    """Transparent greedy approximation for a classroom decision-support demo."""
    stock = {(r.Product, r.Warehouse): float(r.Excess) for r in inventory.itertuples()}
    need = {(r.Product, r.Warehouse): float(r.Shortage) for r in inventory.itertuples()}
    priority = {(r.Product, r.Warehouse): float(r.Priority) for r in inventory.itertuples()}
    unit_cost = {(r["Product"], r["Warehouse"]): float(r["Unit cost"]) for _, r in inventory.iterrows()}
    outbound = {w: float(out_cap) for w in WAREHOUSES}
    inbound = {w: float(in_cap) for w in WAREHOUSES}
    storage = {w: float(storage_cap) for w in WAREHOUSES}
    remaining_budget = float(budget)
    candidates = []
    products = inventory["Product"].unique()
    for product in products:
        sources = [w for w in WAREHOUSES if stock.get((product, w), 0) > 0]
        destinations = [w for w in WAREHOUSES if need.get((product, w), 0) > 0]
        for source in sources:
            for dest in destinations:
                if source == dest:
                    continue
                cost = unit_cost[(product, source)]
                benefit = priority[(product, dest)]
                candidates.append((benefit / max(cost, 1), benefit, product, source, dest, cost))
    candidates.sort(reverse=True)

    plan = []
    for ratio, benefit, product, source, dest, cost in candidates:
        possible = min(stock.get((product, source), 0), need.get((product, dest), 0), outbound[source], inbound[dest], storage[dest], remaining_budget / max(cost, 1))
        qty = int(possible)
        # This simplified prototype uses one truck per lane/product shipment.
        qty = min(qty, int(truck_cap))
        if qty < int(moq) or qty < int(truck_cap * min_fill):
            continue
        expense = qty * cost
        plan.append({"Product": product, "From": source, "To": dest, "Units": qty, "Unit cost (₹)": cost, "Transfer cost (₹)": expense, "Priority": benefit, "Truck fill": qty / truck_cap})
        stock[(product, source)] -= qty
        need[(product, dest)] -= qty
        outbound[source] -= qty
        inbound[dest] -= qty
        storage[dest] -= qty
        remaining_budget -= expense

    return pd.DataFrame(plan), need


st.markdown("<style>\n.stApp{background:#f6f7f5}.block-container{padding-top:2rem;max-width:1320px}.hero{padding:1.5rem 1.8rem;border-radius:18px;background:linear-gradient(120deg,#143c35,#236b5c);color:#fff;margin-bottom:1.2rem}.hero h1{color:#fff;margin:0;font-size:2.2rem}.hero p{color:#d8ebe4;margin:.4rem 0 0}.smallnote{color:#64716d;font-size:.88rem}\n</style>", unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>StockBridge</h1><p>Inventory transfer planner · A Flipkart-inspired classroom prototype</p></div>', unsafe_allow_html=True)
st.caption("Illustrative data only. This prototype demonstrates a simplified greedy heuristic; it is not Flipkart software or a production optimizer.")

with st.sidebar:
    st.subheader("Planning scenario")
    scenario_name = st.selectbox("Choose a scenario", list(SCENARIOS))
    scenario = SCENARIOS[scenario_name]
    budget = st.number_input("Transfer budget (₹)", min_value=0, value=int(scenario["budget"]), step=10_000)
    st.divider()
    st.subheader("Operating limits")
    out_cap = st.number_input("Outbound limit per warehouse (units)", min_value=1, value=160)
    in_cap = st.number_input("Inbound limit per warehouse (units)", min_value=1, value=140)
    storage_cap = st.number_input("Available storage per destination (units)", min_value=1, value=160)
    truck_cap = st.number_input("Truck capacity (units)", min_value=1, value=100)
    min_fill_pct = st.slider("Minimum truck utilization", min_value=0, max_value=100, value=70, step=5)
    moq = st.number_input("Minimum order quantity (units)", min_value=1, value=10)

st.subheader("Inventory position")
default_df = pd.DataFrame(scenario["inventory"])
edited = st.data_editor(default_df, use_container_width=True, hide_index=True, num_rows="fixed", column_config={
    "Warehouse": st.column_config.SelectboxColumn(options=WAREHOUSES),
    "Excess": st.column_config.NumberColumn(min_value=0, step=1),
    "Shortage": st.column_config.NumberColumn(min_value=0, step=1),
    "Priority": st.column_config.NumberColumn(min_value=1, max_value=5, step=1),
    "Unit cost": st.column_config.NumberColumn(min_value=0, step=10, format="₹%.0f"),
})

run = st.button("Generate transfer plan", type="primary", use_container_width=True)
if "plan" not in st.session_state:
    st.session_state.plan = pd.DataFrame()
    st.session_state.remaining = {}
if run:
    if (edited[["Excess", "Shortage", "Priority", "Unit cost"]] < 0).any().any():
        st.error("Inventory, costs, and priorities must be non-negative.")
    elif (edited["Priority"] > 5).any() or (edited["Priority"] < 1).any():
        st.error("Priority must be between 1 and 5.")
    else:
        st.session_state.plan, st.session_state.remaining = recommend_transfers(edited, budget, out_cap, in_cap, storage_cap, truck_cap, min_fill_pct / 100, moq)

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
    st.dataframe(display, use_container_width=True, hide_index=True)
    before_after = []
    for r in edited.itertuples():
        before = float(r.Shortage)
        after = st.session_state.remaining.get((r.Product, r.Warehouse), before)
        before_after.extend([{"Product / centre": f"{r.Product} · {r.Warehouse}", "Measure": "Before", "Units": before}, {"Product / centre": f"{r.Product} · {r.Warehouse}", "Measure": "Remaining", "Units": after}])
    chart = px.bar(pd.DataFrame(before_after), x="Product / centre", y="Units", color="Measure", barmode="group", color_discrete_map={"Before": "#c8d4cf", "Remaining": "#237762"}, title="Shortages before and after the recommended transfers")
    chart.update_layout(legend_title_text="", xaxis_title="", yaxis_title="Units")
    st.plotly_chart(chart, use_container_width=True)
    st.download_button("Download transfer plan (CSV)", plan.to_csv(index=False).encode("utf-8"), file_name="stockbridge_transfer_plan.csv", mime="text/csv")
    st.markdown('<p class="smallnote">Method note: candidates are ranked by destination priority divided by lane unit cost. Quantities are then capped by available stock, shortage, capacity, storage, budget, MOQ, and the simplified one-truck-per-shipment utilization rule. This is an illustrative heuristic, not a solver-generated optimum.</p>', unsafe_allow_html=True)

st.divider()
with st.expander("How to present this prototype"):
    st.markdown("1. Select **Festival Sale** and point out a Bengaluru shortage.\n2. Generate the plan and explain which stock moves, its estimated cost, and remaining shortage.\n3. Switch to **Bengaluru Stockout** and compare.\n4. Change the budget or minimum truck utilization to demonstrate a constraint changing the plan.")
