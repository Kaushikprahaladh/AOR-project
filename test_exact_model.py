import unittest

from exact_model import (
    BUDGET, INBOUND, MOQ, OUTBOUND, PRODUCTS, STORAGE, TRUCK_MAX_LOAD,
    TRUCK_MIN_LOAD, WAREHOUSES, LOAD, lane_cost, scenario_table, solve,
)


class ScenarioDataTests(unittest.TestCase):
    def test_normal_gap_totals_match_written_inputs(self):
        data = scenario_table("Normal Demand")
        self.assertEqual(data["Deficit"].sum(), 428)
        self.assertEqual(data["Excess"].sum(), 612)

    def test_festival_uses_written_ideal_multiplier_and_keeps_stock(self):
        data = scenario_table("Festival Sale")
        self.assertAlmostEqual(data["Deficit"].sum(), 692)
        self.assertAlmostEqual(data["Excess"].sum(), 292.5)

    def test_bengaluru_stockout_total_is_derived_from_changed_on_hand(self):
        data = scenario_table("Bengaluru Stockout")
        self.assertEqual(data["Deficit"].sum(), 1279)


class ExactModelTests(unittest.TestCase):
    def check_plan_invariants(self, scenario):
        plan, summary = solve(scenario)
        self.assertTrue(summary["feasible"], summary)
        self.assertLessEqual(summary["total_cost"], BUDGET + 1e-6)
        for row in plan.itertuples(index=False):
            self.assertGreaterEqual(row.Units, MOQ[row.Product])
            load_points = getattr(row, "_4")
            self.assertGreaterEqual(load_points, TRUCK_MIN_LOAD)
            self.assertLessEqual(load_points, TRUCK_MAX_LOAD)
        for wh in WAREHOUSES:
            out = sum(r["Load points"] for _, r in plan[plan["From"] == wh].iterrows())
            inc = sum(r["Load points"] for _, r in plan[plan["To"] == wh].iterrows())
            self.assertLessEqual(out, OUTBOUND[wh] + 1e-6)
            self.assertLessEqual(inc, INBOUND[wh] + 1e-6)
            self.assertLessEqual(inc, STORAGE[wh] + 1e-6)
        for product in PRODUCTS:
            data = scenario_table(scenario)
            for wh in WAREHOUSES:
                source_excess = data.loc[(data.Product == product) & (data.Warehouse == wh), "Excess"].sum()
                dest_deficit = data.loc[(data.Product == product) & (data.Warehouse == wh), "Deficit"].sum()
                sent = plan.loc[(plan.Product == product) & (plan["From"] == wh), "Units"].sum()
                received = plan.loc[(plan.Product == product) & (plan.To == wh), "Units"].sum()
                self.assertLessEqual(sent, source_excess + 1e-6)
                self.assertLessEqual(received, dest_deficit + 1e-6)
        return plan, summary

    def test_reference_scenarios_respect_constraints(self):
        for scenario in ("Normal Demand", "Festival Sale", "Bengaluru Stockout"):
            with self.subTest(scenario=scenario):
                self.check_plan_invariants(scenario)

    def test_lane_cost_is_rate_times_load_factor(self):
        self.assertEqual(lane_cost("SP", "KOL", "BLR"), 80)
        self.assertEqual(lane_cost("RF", "KOL", "BLR"), 800)
        self.assertEqual(lane_cost("GR", "KOL", "PAT"), 15)


if __name__ == "__main__":
    unittest.main()
