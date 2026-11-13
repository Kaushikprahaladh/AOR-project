# StockBridge exact model handoff

This folder contains the exact mixed-integer optimization model used by the StockBridge Streamlit planner. It uses the fictional data and rules supplied by Kaushik on November 10, 2026. The model also retains fixed reference scenarios for command-line runs and regression checks.

## Files

- `exact_model.py` — single-day MILP and command-line runner.
- `app.py` — Streamlit planner; editable inventory is passed to `exact_model.solve_inventory`.
- `scenario_inputs.csv` — source inventory inputs.
- `test_scenarios.csv` — test design, inputs, expected behavior and the exact-model checks to record.
- `handoff_notes.md` — formulation, assumptions, iteration sequence, limitations, and team review questions.
- `test_exact_model.py` — automated tests for scenario arithmetic, costs, and feasible-plan invariants.
- `reference_results.md` — recorded solver plans and verification status.

## Run

The model requires Python, NumPy, pandas, and SciPy. SciPy's `milp` calls its HiGHS-based solver.

```bash
python -m pip install -r requirements-model.txt
python exact_model.py
```

On Windows PowerShell, if the terminal cannot display the rupee symbol, use `$env:PYTHONIOENCODING='utf-8'; python exact_model.py`.

Run one scenario:

```bash
python exact_model.py --scenario "Normal Demand"
```

Export each plan and summary to CSV:

```bash
python exact_model.py --csv-prefix outputs
```

## Model summary

Integer shipment units are chosen for every product and directed warehouse lane, with one binary activation per product-lane. The first optimization pass maximizes priority-weighted units fulfilled. The second minimizes cost while holding that utility score at its optimum. The reference scenarios enforce budget, aggregate stock/deficit, warehouse load-point capacities, one-truck shipment limits, MOQ, and truck minimum/maximum fill.

The app-facing `solve_inventory` function applies the same two-stage integer-optimization approach to the inventory and operating limits edited in Streamlit. Its controls express capacities in units and use source unit costs and destination priorities from the inventory table. The app displays any remaining deficit with the available-stock or constraint explanation returned by the solver.

The automated tests cover scenario arithmetic and final-plan invariants. The broader T1–T8 matrix in `test_scenarios.csv` is a proposed test plan; several isolated-rule cases still need dedicated configurable tests.
