import os
import pickle
import tempfile
import unittest

import numpy as np

from app.config import Config
from app.models.fraud_model import FraudDetectionModel, ModelUnavailable
from app.routes.prediction import EXAMPLES
from app.utils.schema import FEATURE_NAMES


def vector(example):
    return [float(example['values'][name]) for name in FEATURE_NAMES]


class FourteenColumnModel:
    """Stands in for a classifier fitted on fewer columns than the app sends."""
    n_features_in_ = 14


class FraudDetectionModelTest(unittest.TestCase):
    def setUp(self):
        self.model = FraudDetectionModel(Config.MODEL_PATH)

    def test_the_trained_model_loads_and_takes_twenty_inputs(self):
        estimator = self.model.load_model()
        self.assertEqual(estimator.n_features_in_, 20)
        self.assertEqual(self.model.expected_features, 20)

    def test_worked_examples_get_the_verdict_they_are_named_for(self):
        examples = {example['key']: example for example in EXAMPLES}

        low = self.model.predict(vector(examples['low']))
        self.assertEqual(low['prediction'], 'good')
        self.assertFalse(low['flagged'])
        self.assertLess(low['risk_score'], 25)

        high = self.model.predict(vector(examples['high']))
        self.assertEqual(high['prediction'], 'bad')
        self.assertTrue(high['flagged'])
        self.assertGreater(high['risk_score'], 75)

    def test_an_application_is_flagged_exactly_when_its_score_is_over_fifty(self):
        from train_model import load_dataset
        X, _ = load_dataset()
        for result in self.model.predict_many(X[:200]):
            self.assertTrue(0 <= result['risk_score'] <= 100)
            self.assertEqual(result['flagged'], result['risk_score'] > 50)
            self.assertEqual(result['prediction'], 'bad' if result['flagged'] else 'good')

    def test_many_rows_are_scored_in_one_call(self):
        matrix = np.array([vector(example) for example in EXAMPLES])
        results = self.model.predict_many(matrix)
        self.assertEqual([result['prediction'] for result in results], ['good', 'bad'])

    def test_no_rows_give_no_results(self):
        self.assertEqual(self.model.predict_many(np.empty((0, 20))), [])

    def test_wrong_number_of_inputs_is_refused(self):
        with self.assertRaises(ValueError):
            self.model.predict([1.0] * 14)

    def test_a_missing_model_file_is_reported_with_the_fix(self):
        missing = FraudDetectionModel(os.path.join(tempfile.gettempdir(), 'no-such-model.pkl'))
        with self.assertRaises(ModelUnavailable) as raised:
            missing.predict([1.0] * 20)
        self.assertIn('train_model.py', str(raised.exception))

    def test_an_unreadable_model_file_is_reported_with_the_fix(self):
        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
            f.write(b'not a pickle')
        try:
            with self.assertRaises(ModelUnavailable) as raised:
                FraudDetectionModel(f.name).predict([1.0] * 20)
            self.assertIn('train_model.py', str(raised.exception))
        finally:
            os.remove(f.name)

    def test_a_model_fitted_on_other_columns_is_refused(self):
        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
            pickle.dump(FourteenColumnModel(), f)
        try:
            with self.assertRaises(ModelUnavailable):
                FraudDetectionModel(f.name).predict([1.0] * 20)
        finally:
            os.remove(f.name)


if __name__ == '__main__':
    unittest.main()
