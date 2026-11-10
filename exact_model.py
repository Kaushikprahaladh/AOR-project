"""Exact single-day inter-warehouse transfer MILP for the StockBridge project.

Solver: SciPy's ``milp`` interface, which uses the HiGHS optimization engine.
All scenario data are illustrative. The formulation is a student-scale model,
not a reproduction of Flipkart's production implementation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

WAREHOUSES = ("KOL", "BLR", "PAT")
PRODUCTS = ("SP", "RF", "GR")
LOAD = {"SP": 1.0, "RF": 10.0, "GR": 0.5}
MOQ = {"SP": 75, "RF": 8, "GR": 150}
TRUCK_MIN_LOAD = 70.0
TRUCK_MAX_LOAD = 95.0
LANE_RATE = {
    frozenset(("KOL", "PAT")): 30.0,
    frozenset(("KOL", "BLR")): 80.0,
    frozenset(("PAT", "BLR")): 100.0,
}
OUTBOUND = {"KOL": 220.0, "BLR": 150.0, "PAT": 120.0}
INBOUND = {"KOL": 120.0, "BLR": 100.0, "PAT": 180.0}
STORAGE = {"KOL": 140.0, "BLR": 220.0, "PAT": 110.0}
BUDGET = 12_000.0
ALPHA = 0.5

# Baseline input rows. "Ideal" is desired inventory; on-hand is stock now.
BASE = {
    "SP": {"KOL": (250, 345, .40), "BLR": (400, 290, .45), "PAT": (150, 70, .15)},
    "RF": {"KOL": (30, 12, .35), "BLR": (25, 25, .45), "PAT": (15, 32, .20)},
    "GR": {"KOL": (800, 1100, .35), "BLR": (900, 1100, .40), "PAT": (700, 480, .25)},
}


def scenario_table(name: str) -> pd.DataFrame:
    """Build scenario rows according to the pasted data note, literally."""
    if name not in {"Normal Demand", "Festival Sale", "Bengaluru Stockout"}:
        raise ValueError(f"Unknown scenario: {name}")
    rows = []
    for p, by_wh in BASE.items():
        for w, (ideal, on_hand, share) in by_wh.items():
            adjusted_ideal = ideal
            adjusted_on_hand = on_hand
            if name == "Festival Sale" and w in {"KOL", "PAT"}:
                adjusted_ideal = ideal * 1.3
            if name == "Bengaluru Stockout" and w == "BLR":
                adjusted_on_hand = {"SP": 60, "RF": 4, "GR": 300}[p]
            gap = adjusted_ideal - adjusted_on_hand
            rows.append({
                "Product": p, "Warehouse": w, "Ideal": adjusted_ideal,
                "On hand": adjusted_on_hand, "Gap": gap,
                "Excess": max(-gap, 0), "Deficit": max(gap, 0),
                "Sales share": share,
                "Utility": ALPHA * (max(gap, 0) / adjusted_ideal * 100 if adjusted_ideal else 0) + ALPHA * share * 100,
            })
    return pd.DataFrame(rows)


def lane_cost(product: str, source: str, destination: str) -> float:
    try:
        rate = LANE_RATE[frozenset((source, destination))]
    except KeyError as exc:
        raise ValueError(f"Unknown lane {source}-{destination}") from exc
    return rate * LOAD[product]


def _solve_stage(c, integrality, lower, upper, rows, row_lb, row_ub, options=None):
    matrix = lil_matrix((len(rows), len(c)), dtype=float)
    for ridx, coeffs in enumerate(rows):
        for vidx, value in coeffs.items():
            matrix[ridx, vidx] = value
    return milp(
        c=np.asarray(c, dtype=float),
        integrality=np.asarray(integrality, dtype=int),
        bounds=Bounds(np.asarray(lower, dtype=float), np.asarray(upper, dtype=float)),
        constraints=LinearConstraint(matrix.tocsr(), np.asarray(row_lb, dtype=float), np.asarray(row_ub, dtype=float)),
        options=options or {"disp": False},
    )


def solve(name: str, budget: float = BUDGET) -> Tuple[pd.DataFrame, dict]:
    """Maximize priority-weighted fulfilled units, then minimize cost at that score.

    One binary activation per product-lane, one shipment (one truck) per
    product-lane; integer units. Warehouse capacity/storage is measured in load
    points. All source and destination bounds are aggregate across lanes.
    """
    data = scenario_table(name)
    excess = {(r.Product, r.Warehouse): float(r.Excess) for r in data.itertuples()}
    deficit = {(r.Product, r.Warehouse): float(r.Deficit) for r in data.itertuples()}
    utility = {(r.Product, r.Warehouse): float(r.Utility) for r in data.itertuples()}
    lanes = [(p, s, d) for p in PRODUCTS for s in WAREHOUSES for d in WAREHOUSES if s != d]
    n = len(lanes)
    # Variables are x[0:n] (integer units) and y[n:2n] (binary shipment use).
    lower, upper, integ = [0.0] * n + [0.0] * n, [0.0] * (2 * n), [1] * n + [1] * n
    for i, (p, s, d) in enumerate(lanes):
        upper[i] = min(excess.get((p, s), 0.0), deficit.get((p, d), 0.0))
        upper[n + i] = 1.0

    rows: List[Dict[int, float]] = []
    lbs: List[float] = []
    ubs: List[float] = []
    def add(coeff, lb=-np.inf, ub=np.inf):
        rows.append(coeff); lbs.append(lb); ubs.append(ub)

    # Aggregate inventory bounds; prevents the same source stock / destination
    # need being counted once per lane.
    for p in PRODUCTS:
        for s in WAREHOUSES:
            add({i: 1.0 for i, (pp, ss, dd) in enumerate(lanes) if pp == p and ss == s}, ub=excess.get((p, s), 0.0))
        for d in WAREHOUSES:
            add({i: 1.0 for i, (pp, ss, dd) in enumerate(lanes) if pp == p and dd == d}, ub=deficit.get((p, d), 0.0))

    # Outbound, inbound, and pooled destination free-storage limits in load points.
    for s in WAREHOUSES:
        add({i: LOAD[p] for i, (p, ss, d) in enumerate(lanes) if ss == s}, ub=OUTBOUND[s])
    for d in WAREHOUSES:
        coeff = {i: LOAD[p] for i, (p, s, dd) in enumerate(lanes) if dd == d}
        add(coeff, ub=INBOUND[d])
        add(coeff, ub=STORAGE[d])

    # One selected shipment occupies one truck; MOQ and truck-fill lower bound.
    for i, (p, s, d) in enumerate(lanes):
        load = LOAD[p]
        big_m = min(excess.get((p, s), 0.0), deficit.get((p, d), 0.0))
        add({i: load, n + i: -TRUCK_MAX_LOAD}, ub=0.0)
        min_units = max(MOQ[p], int(np.ceil(TRUCK_MIN_LOAD / load - 1e-10)))
        add({i: -1.0, n + i: min_units}, ub=0.0)
        # Avoid y=1 for an impossible lane; objective itself never benefits from it,
        # but this tightens the model and gives clean binary values.
        if big_m < min_units:
            upper[n + i] = 0.0

    costs = [lane_cost(p, s, d) for p, s, d in lanes]
    add({i: costs[i] for i in range(n)}, ub=budget)

    # Use the utility coefficients directly. Fractional ideals in Festival Sale
    # mean priorities are not guaranteed to land on a fixed decimal grid.
    score = [utility[(p, d)] for p, s, d in lanes]
    objective_1 = [0.0] * (2 * n)
    for i in range(n):
        objective_1[i] = -float(score[i])
    result_1 = _solve_stage(objective_1, integ, lower, upper, rows, lbs, ubs)
    if not result_1.success:
        return pd.DataFrame(), {"scenario": name, "status": result_1.message, "feasible": False}
    optimum_score = float(sum(score[i] * result_1.x[i] for i in range(n)))
    # Lexicographic tie-break: among maximum-utility plans, choose minimum cost.
    rows_2 = list(rows) + [{i: float(score[i]) for i in range(n)}]
    score_tolerance = 1e-7
    lbs_2 = list(lbs) + [optimum_score - score_tolerance]
    ubs_2 = list(ubs) + [optimum_score + score_tolerance]
    objective_2 = costs + [0.0] * n
    result = _solve_stage(objective_2, integ, lower, upper, rows_2, lbs_2, ubs_2)
    chosen = result if result.success else result_1

    plan = []
    for i, (p, s, d) in enumerate(lanes):
        qty = int(round(chosen.x[i]))
        if qty <= 0:
            continue
        load_points = qty * LOAD[p]
        plan.append({"Product": p, "From": s, "To": d, "Units": qty,
                     "Load points": load_points, "Truck fill %": round(load_points / 100 * 100, 1),
                     "Unit cost (₹)": costs[i], "Transfer cost (₹)": qty * costs[i],
                     "Priority": utility[(p, d)], "Weighted utility": qty * utility[(p, d)]})
    plan_df = pd.DataFrame(plan, columns=["Product", "From", "To", "Units", "Load points", "Truck fill %", "Unit cost (₹)", "Transfer cost (₹)", "Priority", "Weighted utility"])
    moved_by = {(p, w): 0 for p in PRODUCTS for w in WAREHOUSES}
    for item in plan:
        moved_by[(item["Product"], item["To"])] += item["Units"]
    remaining = {key: max(0.0, val - moved_by[key]) for key, val in deficit.items()}
    summary = {
        "scenario": name,
        "status": chosen.message,
        "feasible": True,
        "objective_weighted_utility": round(sum(x["Weighted utility"] for x in plan), 4),
        "total_units": int(sum(x["Units"] for x in plan)),
        "total_cost": round(sum(x["Transfer cost (₹)"] for x in plan), 2),
        "initial_deficit_units": int(sum(deficit.values())),
        "remaining_deficit_units": int(round(sum(remaining.values()))),
        "solver": "SciPy milp / HiGHS",
    }
    return plan_df, summary


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("Normal Demand", "Festival Sale", "Bengaluru Stockout"), action="append")
    parser.add_argument("--budget", type=float, default=BUDGET)
    parser.add_argument("--csv-prefix", help="Optional output file prefix for plan/summary CSV files")
    args = parser.parse_args()
    scenarios = args.scenario or ["Normal Demand", "Festival Sale", "Bengaluru Stockout"]
    for name in scenarios:
        plan, summary = solve(name, budget=args.budget)
        print(f"\n{name}: {summary}")
        print(plan.to_string(index=False) if not plan.empty else "No transfers")
        if args.csv_prefix:
            safe = name.lower().replace(" ", "_")
            plan.to_csv(f"{args.csv_prefix}_{safe}_plan.csv", index=False)
            pd.DataFrame([summary]).to_csv(f"{args.csv_prefix}_{safe}_summary.csv", index=False)


if __name__ == "__main__":
    main()
