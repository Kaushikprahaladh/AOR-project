"""Run the T1-T8 StockBridge validation matrix and print observed evidence."""
from __future__ import annotations

import pandas as pd

from exact_model import solve, solve_inventory


def inventory_rows(*rows):
    return pd.DataFrame(rows, columns=["Product", "Warehouse", "Excess", "Shortage", "Priority", "Unit cost"])


def run_case(case_id, description, expected, check):
    try:
        observed, passed = check()
        status = "PASS" if passed else "FAIL"
    except Exception as exc:  # Keep the matrix running so every case is reported.
        observed = f"{type(exc).__name__}: {exc}"
        status = "FAIL"
    print(f"{case_id}\t{status}\t{description}\tExpected: {expected}\tObserved: {observed}")
    return status


def run_inventory(inventory, *, budget=100_000, out=500, inbound=500, storage=500,
                  truck=100, minimum_fill=0.70, moq=1, maximum_fill=0.95):
    return solve_inventory(inventory, budget, out, inbound, storage, truck,
                           minimum_fill, moq, maximum_fill)


def units(plan):
    return int(plan["Units"].sum()) if not plan.empty else 0


def main():
    results = []

    def t1():
        data = inventory_rows(("SP", "KOL", 100, 0, 5, 10), ("SP", "BLR", 0, 0, 5, 10))
        plan, remaining, _ = run_inventory(data)
        return f"{units(plan)} units; plan rows={len(plan)}", units(plan) == 0
    results.append(run_case("T1", "Zero deficits", "0 units, no transfer", t1))

    def t2():
        data = inventory_rows(("SP", "KOL", 95, 0, 5, 10), ("SP", "BLR", 0, 110, 5, 10))
        plan, remaining, _ = run_inventory(data, minimum_fill=0.70, moq=75)
        qty = units(plan)
        fill = float(plan.iloc[0]["Truck fill"]) if not plan.empty else 0
        left = int(remaining[("SP", "BLR")])
        observed = f"{qty} units; {qty} load points; {fill:.0%} fill; {left} unfilled"
        return observed, qty == 95 and left == 15 and abs(fill - 0.95) < 1e-9
    results.append(run_case("T2", "Shipment in truck window", "95 units; 95% fill; 15 unfilled", t2))

    def t3():
        data = inventory_rows(("SP", "KOL", 40, 0, 5, 10), ("SP", "BLR", 0, 70, 5, 10))
        plan, remaining, _ = run_inventory(data, minimum_fill=0, moq=1, maximum_fill=1)
        qty = units(plan)
        return f"{qty} moved; {int(remaining.get(('SP', 'BLR'), 0))} unfilled", qty == 40
    results.append(run_case("T3", "Aggregate source cap only", "40 moved; 30 unfilled", t3))

    def t3b():
        data = inventory_rows(("SP", "KOL", 40, 0, 5, 10), ("SP", "BLR", 0, 70, 5, 10))
        plan, remaining, _ = run_inventory(data, minimum_fill=0.70, moq=75)
        qty = units(plan)
        return f"{qty} moved; {int(remaining.get(('SP', 'BLR'), 0))} unfilled", qty == 0
    results.append(run_case("T3b", "Full rules reject undersized shipment", "0 moved; infeasible lane unused", t3b))

    def t3c():
        data = inventory_rows(("SP", "KOL", 95, 0, 5, 10), ("SP", "BLR", 0, 110, 5, 10), ("SP", "PAT", 0, 80, 5, 10))
        plan, remaining, _ = run_inventory(data, minimum_fill=0.70, moq=75)
        qty = units(plan)
        lane_units = plan["Units"].astype(int).tolist() if not plan.empty else []
        valid = qty <= 95 and all(70 <= lane <= 95 for lane in lane_units)
        return f"{qty} combined units across {len(lane_units)} lane(s): {lane_units}", valid
    results.append(run_case("T3c", "No source stock double-counting", "Combined shipments <=95; each active lane >=70", t3c))

    def t4():
        data = inventory_rows(("SP", "KOL", 100, 0, 1, 100), ("SP", "BLR", 0, 100, 5, 100), ("SP", "PAT", 0, 100, 4, 100))
        observations = []
        for budget in (10_000, 4_000):
            plan, _, _ = run_inventory(data, budget=budget, minimum_fill=0, moq=1, maximum_fill=1)
            observations.append(f"budget {budget}: {plan[['To', 'Units']].to_dict('records')}, spend {int(plan['Transfer cost (₹)'].sum()) if not plan.empty else 0}")
        stated_4000_plan_cost = (20 + 80) * 100
        compatible = stated_4000_plan_cost <= 4_000
        return "; ".join(observations) + "; note's 20+80 at unit cost 100 costs 10000", compatible
    results.append(run_case("T4", "Budget / utility reference expectation", "Note cites BLR 100 at 10000; BLR 20 + PAT 80 at 4000", t4))

    def t5():
        data = inventory_rows(("SP", "KOL", 200, 0, 5, 10), ("SP", "BLR", 0, 150, 5, 10))
        plan, remaining, _ = run_inventory(data, inbound=60, minimum_fill=0, moq=1, maximum_fill=1)
        qty = units(plan)
        return f"{qty} moved; {int(remaining.get(('SP', 'BLR'), 0))} unfilled", qty == 60
    results.append(run_case("T5", "Inbound limit only", "60 units when shipment lower bound is disabled", t5))

    def t6():
        data = inventory_rows(("Small", "KOL", 60, 0, 1, 10), ("Small", "BLR", 0, 60, 1, 10), ("Large", "KOL", 80, 0, 1, 10), ("Large", "BLR", 0, 80, 1, 10))
        plan, _, _ = run_inventory(data, minimum_fill=0, moq=70, maximum_fill=1)
        observed = plan[["Product", "Units"]].to_dict("records") if not plan.empty else []
        passed = units(plan) == 80 and all(row["Product"] == "Large" for row in observed)
        return str(observed), passed
    results.append(run_case("T6", "MOQ threshold", "60-unit candidate rejected; 80-unit candidate allowed", t6))

    def t7():
        data90 = inventory_rows(("SP", "KOL", 90, 0, 5, 10), ("SP", "BLR", 0, 90, 5, 10))
        at70, _, _ = run_inventory(data90, minimum_fill=0.70, moq=1)
        at95, _, _ = run_inventory(data90, minimum_fill=0.95, moq=1)
        data120 = inventory_rows(("SP", "KOL", 120, 0, 5, 10), ("SP", "BLR", 0, 120, 5, 10))
        max_plan, _, _ = run_inventory(data120, minimum_fill=0, moq=1)
        observed = f"90 available: min70% -> {units(at70)}, min95% -> {units(at95)}; 120 available: max95% -> {units(max_plan)}"
        return observed, units(at70) == 90 and units(at95) == 0 and units(max_plan) == 95
    results.append(run_case("T7", "Minimum and maximum truck fill", "90 ships at 70%; rejects at 95%; maximum 95 units", t7))

    def t8():
        output = []
        passed = True
        for name in ("Normal Demand", "Festival Sale", "Bengaluru Stockout"):
            plan, summary = solve(name)
            actual = (summary["total_units"], summary["total_cost"], summary["objective_weighted_utility"], summary["initial_deficit_units"], summary["remaining_deficit_units"])
            output.append(f"{name}: {actual}; plan={plan[['Product','From','To','Units']].to_dict('records') if not plan.empty else []}")
            passed = passed and summary["feasible"] and summary["total_cost"] <= 12_000
        return "; ".join(output), passed
    results.append(run_case("T8", "Three fixed-scenario integrations", "All scenarios feasible and within budget", t8))

    passed_count = results.count("PASS")
    failed_count = results.count("FAIL")
    print(f"TOTAL\t{passed_count} PASS\t{failed_count} FAIL\t{len(results)} cases")


if __name__ == "__main__":
    main()
