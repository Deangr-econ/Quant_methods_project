import unittest

import pandas as pd

from volare_review import reconcile_reviews, weekday_calendar_audit


class ReviewTests(unittest.TestCase):
    def test_joint_omission_is_visible_without_asserting_holiday_closure(self):
        data = pd.DataFrame({"date": pd.to_datetime(["2023-04-06", "2023-04-10"] * 2),
                             "symbol": ["ES", "ES", "CL", "CL"]})
        audit = weekday_calendar_audit(data).set_index("date")
        self.assertEqual(audit.loc["2023-04-07", "observed_count"], 0)
        self.assertEqual(audit.loc["2023-04-07", "candidate_holiday"], "Good Friday")
        self.assertFalse(audit.calendar_verified.any())
        self.assertEqual(len(audit), 3)

    def test_coverage_boundary_is_distinct_from_internal_gap(self):
        data = pd.DataFrame({"date": pd.to_datetime(["2023-01-03", "2023-01-05", "2023-01-02", "2023-01-05"]),
                             "symbol": ["ES", "ES", "CL", "CL"]})
        audit = weekday_calendar_audit(data).set_index("date")
        self.assertTrue(audit.loc["2023-01-02", "ES_outside_coverage"])
        self.assertFalse(audit.loc["2023-01-04", "ES_outside_coverage"])
        self.assertEqual(audit.loc["2023-01-04", "observed_count"], 0)
        self.assertEqual(audit.loc["2023-01-04", "candidate_holiday"], "")

    def test_stale_source_and_changed_flags_cannot_reuse_decision(self):
        flags = pd.DataFrame({"date": pd.to_datetime(["2021-03-29"]), "symbol": ["ES"],
                              "flags": ["low"], "status": ["unreviewed"], "rk": [1.]})
        ledger = flags.drop(columns=["status", "rk"]).assign(
            decision="unresolved", evidence="source", reason="low quote", reviewer="test",
            reviewed_at="2026-09-29", source_sha256="snapshot")
        with self.assertRaisesRegex(ValueError, "hash differs"):
            reconcile_reviews(flags, ledger, "changed")
        with self.assertRaisesRegex(ValueError, "no longer match"):
            reconcile_reviews(flags.assign(flags="new flag"), ledger, "snapshot")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            reconcile_reviews(flags, pd.concat([ledger, ledger]), "snapshot")
        result = reconcile_reviews(flags, ledger, "snapshot")
        self.assertEqual(result.iloc[0].rk, 1.)
        self.assertEqual(result.iloc[0].decision, "unresolved")


if __name__ == "__main__":
    unittest.main()
