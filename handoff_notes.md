# StockBridge model handoff notes

For Priya, Kaushik, Tithi, and Rohit. This is a working model specification to review and refine together; it is not a claim that the fictional values describe Flipkart.

## What the referee model answers

For each product, choose how many units to ship on each directed warehouse lane for one day. The model prioritizes high-utility shortage fulfillment while obeying the given stock, budget, warehouse-capacity, storage, MOQ, and truck-window rules.

## Data and utility

`Ideal` is desired inventory and `On hand` is current inventory. The signed gap is `Ideal - On hand`; positive gap is deficit, negative gap is excess. For a destination with positive gap, the utility is:

`w = 0.5 * (deficit / ideal * 100) + 0.5 * (sales share * 100)`

This follows the supplied note. Utility is multiplied by units in the objective. It is not divided by cost. The model's second pass is a cost tie-break only after maximum utility is fixed.

## Decision variables

- `x[p,s,d]`: integer units of product `p` transferred from source `s` to destination `d`.
- `y[p,s,d]`: binary indicator that the product-lane shipment is used.

There is at most one product-lane shipment (one truck) for this one-day model. A later extension allowing multiple trucks per lane would need indexed truck or shipment variables and should be approved as a change to the assumptions.

## Objective and constraints

Lexicographic objective:

1. Maximize `sum(priority[p,d] * x[p,s,d])`.
2. Among solutions with that exact best score, minimize total transfer cost.

Constraints:

1. Aggregate outgoing units for a product/source cannot exceed its excess.
2. Aggregate incoming units for a product/destination cannot exceed its deficit.
3. Outbound load points per source cannot exceed its daily limit.
4. Inbound load points per destination cannot exceed its daily limit.
5. Inbound load points per destination cannot exceed the pooled free-storage limit.
6. Total cost cannot exceed the budget.
7. If a lane is active, quantity must reach both the product MOQ and 70% truck load.
8. Active shipment load cannot exceed 95% of the truck's 100 load-point capacity.
9. A lane cannot be active if its available excess/deficit is smaller than the required minimum shipment.

Load points/unit: SP 1, RF 10, GR 0.5. Lane rate is rupees per load point. Unit cost is rate times load points/unit.

## Important data audit finding

The source note says Festival Sale multiplies ideal inventory by 1.3 at KOL and PAT only, with on-hand unchanged. Applying that rule literally gives total deficit **692**, matching the note. (KOL and PAT adjusted ideals create larger shortfalls; KOL SP remains excess.)

For Bengaluru Stockout, changing BLR on-hand to SP 60, RF 4, GR 300 while retaining baseline ideals gives total deficit **1,279**, matching the note.

The Normal case totals 428 deficit and 612 excess units; the note's 428 deficit is correct. Its stated plan has KOL outbound load 190 points, BLR inbound 95 and PAT inbound 95, all within limits.

## Model-building iterations

1. Inventory allocation only: aggregate source excess and destination deficit. Confirm total moved units cannot double-count stock or demand.
2. Add utility maximization and budget. Record utility and spend.
3. Add outbound limits, then inbound limits, then pooled storage. Record changes after each addition.
4. Add activation binaries, MOQ, and one-truck minimum/maximum fill. Record rejected small shipments.
5. Add the cost tie-break and compare the exact output with the Streamlit planner. The app now calls the app-facing exact inventory solver; it no longer uses a separate greedy heuristic.

The current `exact_model.py` implements the reference model and an app-facing inventory solver with the same two-stage objective. The iteration waterfall in the supplied note is a proposed reference; re-run each iteration in a separately versioned model before citing it as reproduced evidence. Run `python run_test_matrix.py` for the T1–T8 validation matrix; see `reference_results.md` for captured outputs and the unresolved T4 expected-result mismatch.

## What to ask the team to fine-tune

- Confirm the scenario transformations and corrected deficit totals above.
- Confirm whether storage is truly pooled across products and whether existing on-hand stock consumes any of the stated free storage.
- Confirm that one product-lane truck is the intended assumption and whether mixed-product loads or multiple trucks should be modeled.
- Decide how to handle fractional ideal inventories created by the 1.3 multiplier. This script permits fractional gaps but shipment units are integer.
- Confirm the priority utility formula and whether it should use deficit as a share of ideal inventory.
- Agree how integer priorities are scaled in the solver and what numerical tolerance is acceptable for the utility tie-break.
- Reconcile exact-model outputs with the prototype and write observed test results in the wiki.

## Suggested owner split

- Kaushik: verify data derivations, scenario totals, and test expectations.
- Priya: inspect the MILP implementation and adapt it to the app's data interface.
- Tithi: keep model terms, assumptions, and claims consistent in the wiki.
- Rohit: run the test matrix, capture actual outputs, and record pass/fail evidence.
