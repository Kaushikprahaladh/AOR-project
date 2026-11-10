# StockBridge exact model handoff

This folder contains an exact mixed-integer optimization model intended as a referee for the simplified StockBridge prototype. It uses the fictional data and rules supplied by Kaushik on November 10, 2026.

## Files

- `exact_model.py` — single-day MILP and command-line runner.
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

Integer shipment units are chosen for every product and directed warehouse lane, with one binary activation per product-lane. The first optimization pass maximizes priority-weighted units fulfilled. The second minimizes cost while holding that utility score at its optimum. Budget, aggregate stock/deficit, aggregate warehouse load-point capacities, one-truck shipment limits, MOQ, and truck minimum/maximum fill are enforced.

The output should be compared with the Streamlit prototype. Any difference should be explained as a model mismatch or documented heuristic gap, not silently overwritten.

The automated tests cover scenario arithmetic and final-plan invariants. The broader T1–T8 matrix in `test_scenarios.csv` is a proposed test plan; several isolated-rule cases still need dedicated configurable tests.
