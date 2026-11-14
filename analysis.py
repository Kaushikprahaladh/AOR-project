"""Comparison helpers for exact and greedy StockBridge planning methods."""
from __future__ import annotations

import math
from typing import Dict

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

MILP = "Exact optimizer (MILP)"
GREEDY_SHORTAGE = "Greedy: largest shortage first"
GREEDY_PRIORITY = "Greedy: highest priority first"
TRUCK_MAX_FILL = 0.95


def _solve_stage(objective, rows, lower_bounds, upper_bounds, variable_upper):
    matrix = lil_matrix((len(rows), len(objective)), dtype=float)
    for row_index, coefficients in enumerate(rows):
        for variable_index, coefficient in coefficients.items():
            matrix[row_index, variable_index] = coefficient
    result = milp(
        c=np.asarray(objective, dtype=float),
        integrality=np.ones(len(objective), dtype=int),
        bounds=Bounds(np.zeros(len(objective)), np.asarray(variable_upper, dtype=float)),
        constraints=LinearConstraint(
            matrix.tocsr(), np.asarray(lower_bounds, dtype=float),
            np.asarray(upper_bounds, dtype=float),
        ),
        options={"disp": False},
    )
    if not result.success:
        raise RuntimeError(f"Exact comparison optimization failed: {result.message}")
    return result


def _exact_plan(inventory, *, budget, out_cap, in_cap, storage_cap,
                truck_cap, min_fill, moq):
    products = tuple(dict.fromkeys(row["Product"] for row in inventory))
    warehouses = tuple(dict.fromkeys(row["Warehouse"] for row in inventory))
    if len(warehouses) < 2:
        return []
    by_key = {(row["Product"], row["Warehouse"]): row for row in inventory}
    stock = {(p, w): float(by_key.get((p, w), {}).get("Excess", 0))
             for p in products for w in warehouses}
    need = {(p, w): float(by_key.get((p, w), {}).get("Shortage", 0))
            for p in products for w in warehouses}
    priority = {(p, w): float(by_key.get((p, w), {}).get("Priority", 0))
                for p in products for w in warehouses}
    unit_cost = {(p, w): float(by_key.get((p, w), {}).get("Unit cost", 0))
                 for p in products for w in warehouses}
    lanes = [(p, source, destination) for p in products for source in warehouses
             for destination in warehouses if source != destination]
    count = len(lanes)
    minimum = max(int(moq), int(math.ceil(truck_cap * min_fill - 1e-10)))
    maximum = int(math.floor(truck_cap * TRUCK_MAX_FILL + 1e-10))
    upper = [0.0] * count + [1.0] * count
    costs = []
    weights = []
    for index, (product, source, destination) in enumerate(lanes):
        available = min(stock[(product, source)], need[(product, destination)])
        upper[index] = available
        if available < minimum:
            upper[count + index] = 0.0
        costs.append(unit_cost[(product, source)])
        weights.append(priority[(product, destination)])

    rows = []
    row_lower = []
    row_upper = []

    def add(coefficients, low=-np.inf, high=np.inf):
        rows.append(coefficients)
        row_lower.append(low)
        row_upper.append(high)

    for product in products:
        for source in warehouses:
            add({i: 1.0 for i, (p, s, _) in enumerate(lanes)
                 if p == product and s == source}, high=stock[(product, source)])
        for destination in warehouses:
            add({i: 1.0 for i, (p, _, d) in enumerate(lanes)
                 if p == product and d == destination}, high=need[(product, destination)])
    for warehouse in warehouses:
        add({i: 1.0 for i, (_, source, _) in enumerate(lanes) if source == warehouse}, high=out_cap)
        add({i: 1.0 for i, (_, _, destination) in enumerate(lanes) if destination == warehouse}, high=in_cap)
        add({i: 1.0 for i, (_, _, destination) in enumerate(lanes) if destination == warehouse}, high=storage_cap)
    for i, _ in enumerate(lanes):
        add({i: 1.0, count + i: -float(maximum)}, high=0.0)
        add({i: -1.0, count + i: float(minimum)}, high=0.0)
    add({i: costs[i] for i in range(count)}, high=budget)

    objective = [-weights[i] for i in range(count)] + [0.0] * count
    first = _solve_stage(objective, rows, row_lower, row_upper, upper)
    best_score = float(sum(weights[i] * first.x[i] for i in range(count)))
    score_rows = rows + [{i: weights[i] for i in range(count)}]
    second = _solve_stage(
        costs + [0.0] * count,
        score_rows,
        row_lower + [best_score - 1e-7],
        row_upper + [best_score + 1e-7],
        upper,
    )
    plan = []
    for i, (product, source, destination) in enumerate(lanes):
        quantity = int(round(second.x[i]))
        if quantity <= 0:
            continue
        plan.append({
            "Product": product, "From": source, "To": destination,
            "Units": quantity, "Unit cost (₹)": costs[i],
            "Transfer cost (₹)": quantity * costs[i],
            "Priority": weights[i], "Truck fill": quantity / truck_cap,
        })
    return plan


def _greedy_plan(inventory, *, budget, out_cap, in_cap, storage_cap,
                 truck_cap, min_fill, moq, order_by):
    warehouses = tuple(dict.fromkeys(row["Warehouse"] for row in inventory))
    by_key = {(row["Product"], row["Warehouse"]): row for row in inventory}
    stock = {(p, w): float(by_key.get((p, w), {}).get("Excess", 0))
             for p in dict.fromkeys(row["Product"] for row in inventory) for w in warehouses}
    need = {(p, w): float(by_key.get((p, w), {}).get("Shortage", 0))
            for p in dict.fromkeys(row["Product"] for row in inventory) for w in warehouses}
    outbound = {w: float(out_cap) for w in warehouses}
    inbound = {w: float(in_cap) for w in warehouses}
    storage = {w: float(storage_cap) for w in warehouses}
    remaining_budget = float(budget)
    minimum = max(int(moq), int(math.ceil(truck_cap * min_fill - 1e-10)))
    maximum = int(math.floor(truck_cap * TRUCK_MAX_FILL + 1e-10))
    candidates = []
    products = dict.fromkeys(row["Product"] for row in inventory)
    for product in products:
        for destination in warehouses:
            demand = need[(product, destination)]
            target = by_key.get((product, destination), {})
            if demand <= 0:
                continue
            for source in warehouses:
                source_row = by_key.get((product, source), {})
                if source == destination or stock[(product, source)] <= 0:
                    continue
                if order_by == "shortage":
                    rank = (demand, float(target.get("Priority", 0)))
                else:
                    rank = (float(target.get("Priority", 0)), demand)
                candidates.append((rank, product, source, destination))
    candidates.sort(key=lambda item: (item[0], item[1], item[2], item[3]), reverse=True)
    plan = []
    for _, product, source, destination in candidates:
        cost = float(by_key[(product, source)]["Unit cost"])
        affordable = remaining_budget / cost if cost > 0 else maximum
        quantity = int(math.floor(min(
            stock[(product, source)], need[(product, destination)],
            outbound[source], inbound[destination], storage[destination], maximum,
            affordable,
        ) + 1e-10))
        if quantity < minimum:
            continue
        priority = float(by_key[(product, destination)]["Priority"])
        spend = quantity * cost
        plan.append({
            "Product": product, "From": source, "To": destination,
            "Units": quantity, "Unit cost (₹)": cost,
            "Transfer cost (₹)": spend, "Priority": priority,
            "Truck fill": quantity / truck_cap,
        })
        stock[(product, source)] -= quantity
        need[(product, destination)] -= quantity
        outbound[source] -= quantity
        inbound[destination] -= quantity
        storage[destination] -= quantity
        remaining_budget -= spend
    return plan


def _summary(method, plan):
    return {
        "Method": method,
        "Units transferred": sum(row["Units"] for row in plan),
        "Priority-weighted units": sum(row["Units"] * row["Priority"] for row in plan),
        "Spend (₹)": sum(row["Transfer cost (₹)"] for row in plan),
    }


def compare_methods(inventory, *, budget, out_cap, in_cap, storage_cap,
                    truck_cap, min_fill, moq):
    """Compare the MILP with two feasible one-pass greedy baselines."""
    exact = _exact_plan(
        inventory, budget=budget, out_cap=out_cap, in_cap=in_cap,
        storage_cap=storage_cap, truck_cap=truck_cap, min_fill=min_fill, moq=moq,
    )
    shortage_first = _greedy_plan(
        inventory, budget=budget, out_cap=out_cap, in_cap=in_cap,
        storage_cap=storage_cap, truck_cap=truck_cap, min_fill=min_fill,
        moq=moq, order_by="shortage",
    )
    priority_first = _greedy_plan(
        inventory, budget=budget, out_cap=out_cap, in_cap=in_cap,
        storage_cap=storage_cap, truck_cap=truck_cap, min_fill=min_fill,
        moq=moq, order_by="priority",
    )
    return [
        _summary(MILP, exact),
        _summary(GREEDY_SHORTAGE, shortage_first),
        _summary(GREEDY_PRIORITY, priority_first),
    ]


def budget_sweep(inventory, budgets, *, out_cap, in_cap, storage_cap,
                 truck_cap, min_fill, moq):
    """Evaluate each method at each supplied budget for sensitivity plotting."""
    rows = []
    for budget in budgets:
        comparison = compare_methods(
            inventory, budget=budget, out_cap=out_cap, in_cap=in_cap,
            storage_cap=storage_cap, truck_cap=truck_cap,
            min_fill=min_fill, moq=moq,
        )
        rows.extend({"Budget (₹)": float(budget), **result} for result in comparison)
    return rows
