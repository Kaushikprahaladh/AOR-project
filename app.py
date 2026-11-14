"""Streamlit panel: does the exact optimizer beat simple rules? (illustrative data only)"""
from html import escape

import plotly.graph_objects as go
import streamlit as st

from analysis import budget_sweep, compare_methods

# Constructed stress test (NOT realistic data): a greedy rule ships 95 grocery units,
# leaving 50 outbound units, below the 70-unit minimum; the MILP plans two shipments totaling 145.
STRESS_SCENARIO = {
    "budget": 25_000,
    "inventory": [
        {"Product": "Smartphones", "Warehouse": "Kolkata", "Excess": 80, "Shortage": 0, "Priority": 4, "Unit cost": 210},
        {"Product": "Smartphones", "Warehouse": "Bengaluru", "Excess": 0, "Shortage": 90, "Priority": 1, "Unit cost": 210},
        {"Product": "Grocery packs", "Warehouse": "Kolkata", "Excess": 100, "Shortage": 0, "Priority": 5, "Unit cost": 60},
        {"Product": "Grocery packs", "Warehouse": "Bengaluru", "Excess": 0, "Shortage": 100, "Priority": 2, "Unit cost": 60},
    ],
}
STRESS_NAME = "Capacity Squeeze (stress test)"
SCENARIOS = {
    "Festival Sale": {
        "budget": 180_000, "out_cap": 160, "in_cap": 140, "storage_cap": 160,
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
        "budget": 140_000, "out_cap": 160, "in_cap": 140, "storage_cap": 160,
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
        "budget": 100_000, "out_cap": 160, "in_cap": 140, "storage_cap": 160,
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
    STRESS_NAME: {
        "budget": STRESS_SCENARIO["budget"], "out_cap": 145,
        "in_cap": 250, "storage_cap": 250,
        "inventory": STRESS_SCENARIO["inventory"],
    },
}
MILP = "Exact optimizer (MILP)"


def render_table(rows, class_name):
    if not rows:
        return
    headers = list(rows[0])
    head = "".join(f"<th>{escape(str(label))}</th>" for label in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(row[label]))}</td>" for label in headers) + "</tr>"
        for row in rows
    )
    st.markdown(
        f'<div class="table-scroll"><table class="{class_name}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def render_comparison(edited, **params) -> None:
    st.divider()
    st.markdown('<div class="section-label"><span>02</span> THE HEAD-TO-HEAD</div>', unsafe_allow_html=True)
    st.subheader("Does the optimizer see a better move?")
    st.markdown(
        '<p class="section-copy">All three methods get the same inventory and limits. '
        'The greedy rules commit to the next biggest shortage or highest priority; '
        'the MILP plans across lanes before it commits.</p>',
        unsafe_allow_html=True,
    )
    signature = (tuple(tuple(sorted(row.items())) for row in edited), tuple(sorted(params.items())))
    if st.button("Compare against greedy rules", key="compare_button"):
        try:
            budget = float(params["budget"])
            budgets = [budget * f for f in (0.1, 0.25, 0.5, 0.75, 1.0, 1.5)] if budget > 0 else [0]
            sweep_params = {key: value for key, value in params.items() if key != "budget"}
            st.session_state.comparison = {
                "signature": signature,
                "table": compare_methods(edited, **params),
                "sweep": budget_sweep(edited, budgets, **sweep_params),
            }
        except Exception as exc:  # show a readable message instead of a stack trace
            st.error(f"Comparison failed: {exc}")
            return
    data = st.session_state.get("comparison")
    if not data:
        return
    if data["signature"] != signature:
        st.warning("Inputs changed since this comparison was run. Click the button again to refresh.")

    table = data["table"]
    display_names = {
        MILP: "Exact MILP",
        "Greedy: largest shortage first": "Greedy · shortage first",
        "Greedy: highest priority first": "Greedy · priority first",
    }
    display_table = [
        {
            "Method": display_names[row["Method"]],
            "Units": f"{row['Units transferred']:,}",
            "Weighted score": f"{row['Priority-weighted units']:,.0f}",
            "Spend": f"₹{row['Spend (₹)']:,.0f}",
        }
        for row in table
    ]
    render_table(display_table, "comparison-table")

    m = next(row for row in table if row["Method"] == MILP)
    greedy = [row for row in table if row["Method"] != MILP]
    g = max(greedy, key=lambda row: row["Priority-weighted units"])
    gain = m["Priority-weighted units"] - g["Priority-weighted units"]
    kpis = st.columns(3)
    kpis[0].metric("Exact MILP score", f"{m['Priority-weighted units']:,.0f}")
    kpis[1].metric("Best greedy score", f"{g['Priority-weighted units']:,.0f}")
    kpis[2].metric("MILP edge", f"{gain:+,.0f}")
    if gain > 0:
        extra = m["Spend (₹)"] - g["Spend (₹)"]
        msg = f"The exact plan gains **{gain:,.0f} priority-weighted units** over the best greedy rule."
        if extra > 0:
            msg += f" It spends ₹{extra:,.0f} more (₹{extra / gain:,.0f} per extra weighted unit), so judge whether that is worth it."
        st.success(msg)
    else:
        st.info("On this input a simple rule matches the optimizer. The optimizer can only help when "
                "constraints interact (capacity, MOQ, budget); it is never worse than a greedy rule.")

    colors = ["#245bff" if row["Method"] == MILP else "#ff4e9b" for row in table]
    chart_methods = [display_names[row["Method"]] for row in table]
    max_score = max(row["Priority-weighted units"] for row in table)
    chart = go.Figure(go.Bar(
        x=[row["Priority-weighted units"] for row in table],
        y=chart_methods,
        orientation="h", marker_color=colors,
        text=[f"{row['Priority-weighted units']:,.0f}" for row in table],
        textposition="outside", cliponaxis=False,
    ))
    chart.update_layout(
        title="Priority-weighted units fulfilled", height=300,
        xaxis={"title": "Weighted units", "range": [0, max_score * 1.25]},
        yaxis_title="", showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 12, "r": 18, "t": 60, "b": 24},
        font={"family": "Arial, sans-serif", "color": "#24242a", "size": 12},
        title_font={"family": "Arial, sans-serif", "size": 16, "color": "#111111"},
    )
    st.plotly_chart(chart, width="stretch")

    st.markdown('<div class="section-label"><span>03</span> BUDGET SENSITIVITY</div>', unsafe_allow_html=True)
    st.markdown("### What does more budget buy?")
    sweep = data["sweep"]
    line = go.Figure()
    for method in dict.fromkeys(row["Method"] for row in sweep):
        method_rows = [row for row in sweep if row["Method"] == method]
        color = "#245bff" if method == MILP else "#ff4e9b"
        line.add_trace(go.Scatter(
            x=[row["Budget (₹)"] for row in method_rows],
            y=[row["Priority-weighted units"] for row in method_rows],
            mode="lines+markers", name=method, line={"color": color, "width": 3},
        ))
    line.update_layout(
        height=370, legend_title_text="", xaxis_title="Budget (₹)",
        yaxis_title="Priority-weighted units", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 12, "r": 18, "t": 30, "b": 76},
        legend={"orientation": "h", "y": -0.3, "x": 0, "title_text": ""},
        font={"family": "Arial, sans-serif", "color": "#24242a", "size": 12},
    )
    st.plotly_chart(line, width="stretch")


st.set_page_config(page_title="StockBridge | Optimizer vs Greedy", page_icon="📦", layout="wide")
with st.sidebar:
    st.subheader("Planning scenario")
    scenario_name = st.selectbox("Choose a scenario", list(SCENARIOS))
    scenario = SCENARIOS[scenario_name]
    budget = st.number_input(
        "Budget (₹)", min_value=0, value=scenario["budget"], step=10_000,
        key=f"budget_{scenario_name}",
    )
    st.divider()
    st.subheader("Shared constraints")
    out_cap = st.number_input(
        "Outbound capacity (units)", min_value=1, value=scenario["out_cap"],
        key=f"outbound_{scenario_name}",
    )
    in_cap = st.number_input(
        "Inbound capacity (units)", min_value=1, value=scenario["in_cap"],
        key=f"inbound_{scenario_name}",
    )
    storage_cap = st.number_input(
        "Storage capacity (units)", min_value=1, value=scenario["storage_cap"],
        key=f"storage_{scenario_name}",
    )
    truck_cap = st.number_input("Truck capacity (units)", min_value=1, value=100, key=f"truck_{scenario_name}")
    min_fill = st.slider("Minimum truck fill", 0, 100, 70, 5, key=f"fill_{scenario_name}") / 100
    moq = st.number_input("Minimum order quantity", min_value=1, value=10, key=f"moq_{scenario_name}")

st.markdown("""
<style>
.stApp{background:#f4f0e2;background-image:radial-gradient(#17171717 .8px,transparent .8px);background-size:15px 15px}
.block-container{max-width:1250px;padding-top:2rem;padding-bottom:4rem}
.hero{position:relative;overflow:hidden;padding:28px 30px;background:#d8ff3e;border:3px solid #111;box-shadow:8px 8px 0 #111;margin:4px 8px 25px 0}
.hero::after{content:none}
.hero-kicker{display:inline-block;padding:5px 8px;background:#ff4e9b;border:2px solid #111;font-size:.72rem;font-weight:950;letter-spacing:1px;text-transform:uppercase}
.hero h1{position:relative;z-index:1;margin:14px 0 8px;font-family:'Arial Black',Impact,sans-serif!important;font-size:3.6rem;line-height:1;color:#111;letter-spacing:0}
.hero p{position:relative;z-index:1;max-width:720px;margin:0;color:#222;font-size:1.04rem;font-weight:650;line-height:1.5}
.section-label{display:flex;align-items:center;gap:9px;margin:1.4rem 0 .4rem;color:#41414b;font-size:.72rem;font-weight:950;letter-spacing:1px}
.section-label span{padding:4px 7px;background:#111;color:#d8ff3e;border:1px solid #111}
.section-copy{max-width:800px;color:#444;font-size:.96rem;line-height:1.5}
h2,h3{font-family:'Arial Black',Impact,sans-serif!important;color:#111!important;letter-spacing:0}
[data-testid="stMetric"]{height:100%;padding:14px 16px;background:#fff;border:2px solid #111;box-shadow:4px 4px 0 #111}
[data-testid="stMetricLabel"]{font-weight:800;color:#555!important}
[data-testid="stMetricValue"]{font-family:'Arial Black',Impact,sans-serif;color:#111}
[data-testid="stButton"] button{min-height:48px;background:#111;color:#d8ff3e;border:2px solid #111;border-radius:3px;box-shadow:4px 4px 0 #ff4e9b;font-weight:900}
[data-testid="stButton"] button:hover{background:#245bff;color:white;border-color:#111}
[data-testid="stNumberInput"] input{border:2px solid #111;border-radius:3px;background:white}
[data-testid="stSlider"] [role="slider"]{background:#ff4e9b}
[data-testid="stSidebar"]{background:#e8e1ce;border-right:2px solid #111}
.table-scroll{overflow-x:auto;margin:10px 6px 20px 0;border:2px solid #111;box-shadow:5px 5px 0 #245bff;background:white}
.comparison-table,.inventory-table{width:100%;border-collapse:collapse;min-width:560px}
.comparison-table{min-width:0;table-layout:fixed}
.comparison-table th,.comparison-table td{white-space:normal;overflow-wrap:anywhere}
.comparison-table th:first-child,.comparison-table td:first-child{width:39%}
.comparison-table th:nth-child(2),.comparison-table td:nth-child(2){width:14%}
.comparison-table th:nth-child(3),.comparison-table td:nth-child(3){width:25%}
.comparison-table th:nth-child(4),.comparison-table td:nth-child(4){width:22%}
.inventory-table{min-width:0;table-layout:fixed}
.inventory-table th,.inventory-table td{white-space:normal;overflow-wrap:anywhere;padding:10px 8px}
.inventory-table th:nth-child(1),.inventory-table td:nth-child(1){width:24%}
.inventory-table th:nth-child(2),.inventory-table td:nth-child(2){width:20%}
.inventory-table th:nth-child(3),.inventory-table td:nth-child(3){width:13%}
.inventory-table th:nth-child(4),.inventory-table td:nth-child(4){width:15%}
.inventory-table th:nth-child(5),.inventory-table td:nth-child(5){width:12%}
.inventory-table th:nth-child(6),.inventory-table td:nth-child(6){width:16%}
.comparison-table th,.inventory-table th{padding:12px 14px;text-align:left;background:#111;color:#d8ff3e;font-size:.75rem;text-transform:uppercase;white-space:nowrap}
.comparison-table td,.inventory-table td{padding:12px 14px;border-bottom:1px solid #ddd;color:#161616;font-weight:650;white-space:nowrap}
.comparison-table tbody tr:first-child{background:#eaf0ff}
.comparison-table tbody tr:nth-child(even),.inventory-table tbody tr:nth-child(even){background:#fff0f7}
@media(max-width:680px){.hero{padding:20px}.hero h1{font-size:2rem}.hero p{font-size:.92rem}.block-container{padding:1rem .8rem 3rem}.comparison-table th,.comparison-table td,.inventory-table th,.inventory-table td{padding:8px 6px;font-size:.78rem}[data-testid="stHorizontalBlock"]{flex-wrap:wrap!important;gap:.45rem!important}[data-testid="stHorizontalBlock"]>[data-testid="column"]{flex:1 1 calc(50% - .45rem)!important;width:calc(50% - .45rem)!important;min-width:calc(50% - .45rem)!important}}
</style>
""", unsafe_allow_html=True)
hero_copy = (
    "A capacity-squeeze demonstration: compare an optimizer that plans across lanes with greedy rules."
    if scenario_name == STRESS_NAME
    else "Compare exact, priority-weighted transfer planning across your selected demand scenario."
)
st.markdown(
    f'<header class="hero"><span class="hero-kicker">INVENTORY TRANSFER PLANNER</span>'
    f'<h1>StockBridge</h1><p>{escape(hero_copy)}</p></header>',
    unsafe_allow_html=True,
)
st.markdown('<div class="section-label"><span>01</span> INVENTORY POSITION</div>', unsafe_allow_html=True)
st.subheader(scenario_name)
st.caption("Edit inventory quantities, destination priorities, and unit costs. Scenario values are illustrative.")
edited = [dict(row) for row in scenario["inventory"]]

total_excess = sum(row["Excess"] for row in edited)
total_shortage = sum(row["Shortage"] for row in edited)
matched_products = set()
for product in dict.fromkeys(row["Product"] for row in edited):
    product_rows = [row for row in edited if row["Product"] == product]
    if any(
        source["Warehouse"] != destination["Warehouse"]
        for source in product_rows if source["Excess"] > 0
        for destination in product_rows if destination["Shortage"] > 0
    ):
        matched_products.add(product)
position_metrics = st.columns(3)
position_metrics[0].metric("Excess inventory", f"{total_excess:,} units")
position_metrics[1].metric("Shortage demand", f"{total_shortage:,} units")
position_metrics[2].metric("Products with a cross-center match", f"{len(matched_products)} / {len(set(row['Product'] for row in edited))}")

inventory_columns = st.columns([1.25, 1.0, 0.9, 0.9, 0.9, 1.0])
for column, heading in zip(inventory_columns, ["Product", "Warehouse", "Excess", "Shortage", "Priority", "Unit cost"]):
    column.markdown(f"**{heading}**")
for row_index, row in enumerate(edited):
    columns = st.columns([1.25, 1.0, 0.9, 0.9, 0.9, 1.0])
    columns[0].write(row["Product"])
    columns[1].write(row["Warehouse"])
    edited[row_index]["Excess"] = columns[2].number_input(
        f"Excess for {row['Product']} at {row['Warehouse']}", min_value=0,
        value=int(row["Excess"]), step=1,
        key=f"{scenario_name}_{row_index}_excess", label_visibility="collapsed",
    )
    edited[row_index]["Shortage"] = columns[3].number_input(
        f"Shortage for {row['Product']} at {row['Warehouse']}", min_value=0,
        value=int(row["Shortage"]), step=1,
        key=f"{scenario_name}_{row_index}_shortage", label_visibility="collapsed",
    )
    edited[row_index]["Priority"] = columns[4].number_input(
        f"Priority for {row['Product']} at {row['Warehouse']}",
        min_value=1, max_value=5, value=int(row["Priority"]), step=1,
        key=f"{scenario_name}_{row_index}_priority", label_visibility="collapsed",
    )
    edited[row_index]["Unit cost"] = columns[5].number_input(
        f"Unit cost for {row['Product']} at {row['Warehouse']}", min_value=0,
        value=int(row["Unit cost"]), step=10,
        key=f"{scenario_name}_{row_index}_unit_cost", label_visibility="collapsed",
    )

render_comparison(
    edited,
    budget=budget,
    out_cap=out_cap,
    in_cap=in_cap,
    storage_cap=storage_cap,
    truck_cap=truck_cap,
    min_fill=min_fill,
    moq=moq,
)