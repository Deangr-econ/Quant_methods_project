from pathlib import Path
import unittest
import numpy as np
import pandas as pd

from final_model_data import prepare_final_data, validate_final_frame

ROOT = Path(__file__).resolve().parents[1]


class FinalDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = pd.read_csv(ROOT / 'datasets/vol_data_futures_yield_final_version.csv', float_precision='round_trip')

    def test_main_models_do_not_require_missing_auxiliary_fields(self):
        frame = validate_final_frame(self.raw)
        self.assertEqual(len(frame), len(self.raw))
        self.assertNotIn('rk_ES', frame)
        self.assertNotIn('open_price_ES', frame)

    def test_duplicate_dates_and_wrong_return_units_are_rejected(self):
        duplicate = pd.concat([self.raw.iloc[:2], self.raw.iloc[1:2]], ignore_index=True)
        with self.assertRaises(ValueError):
            validate_final_frame(duplicate)
        altered = self.raw.copy()
        altered['ret_ES'] /= 100
        with self.assertRaises(ValueError):
            validate_final_frame(altered)

    def test_inconsistent_variance_logs_are_rejected(self):
        altered = self.raw.copy()
        altered.loc[30, 'log_rv5_ES'] += 1
        with self.assertRaises(ValueError):
            validate_final_frame(altered)

    def test_variance_windows_use_only_current_and_past_final_rows(self):
        frame, excluded = prepare_final_data(self.raw)
        self.assertEqual(len(excluded), 21)
        target_date = frame.index[40]
        expected = np.log(self.raw.set_index('date').rv5_ES).iloc[40:62].mean()
        self.assertAlmostEqual(frame.loc[target_date, 'log_rv5_m_ES'], expected)
        altered = self.raw.copy()
        future = pd.to_datetime(altered.date) > target_date
        altered.loc[future, 'rv5_ES'] *= 3
        altered.loc[future, 'log_rv5_ES'] = np.log(altered.loc[future, 'rv5_ES'])
        second, _ = prepare_final_data(altered)
        self.assertAlmostEqual(frame.loc[target_date, 'log_rv5_m_ES'], second.loc[target_date, 'log_rv5_m_ES'])


if __name__ == '__main__':
    unittest.main()
