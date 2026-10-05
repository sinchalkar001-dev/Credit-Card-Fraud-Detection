import os
import unittest

import numpy as np
import pandas as pd

from app.utils.preprocessing import DataPreprocessor
from app.utils.schema import FEATURE_NAMES
from app.utils.validators import PredictionValidator
from tests.test_validators import VALID_RAW

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET = os.path.join(ROOT, 'data', 'credit_data.csv')
SAMPLE = os.path.join(ROOT, 'data', 'sample_upload.csv')

FIRST_ROW = [1, 6, 5, 4, 1169, 1, 5, 4, 1, 1, 4, 1, 67, 1, 1, 2, 3, 1, 1, 1]
SECOND_ROW = [2, 48, 3, 4, 5951, 2, 3, 2, 4, 1, 2, 1, 22, 1, 1, 1, 3, 1, 2, 1]


class PredictionInputTest(unittest.TestCase):
    def test_single_input_is_ordered_for_the_model(self):
        shuffled = dict(reversed(list(VALID_RAW.items())))
        array = DataPreprocessor().preprocess_prediction_input(shuffled)
        self.assertEqual(array.shape, (1, 20))
        self.assertEqual(array[0].tolist(), FIRST_ROW)

    def test_single_input_that_cannot_be_read_raises(self):
        with self.assertRaises(ValueError):
            DataPreprocessor().preprocess_prediction_input({'credit_usage': 6})


class BatchTest(unittest.TestCase):
    def setUp(self):
        self.preprocessor = DataPreprocessor()

    def test_the_bundled_dataset_is_read_as_written(self):
        df = pd.read_csv(DATASET, encoding='unicode_escape')
        self.assertEqual(PredictionValidator.validate_csv_structure(df), (True, ''))

        batch = self.preprocessor.prepare_batch(df)

        self.assertEqual(batch.matrix.shape, (1000, 20))
        self.assertEqual(batch.errors, {})
        self.assertEqual(batch.positions, list(range(1000)))
        self.assertEqual(batch.matrix[0].tolist(), FIRST_ROW)
        self.assertEqual(batch.matrix[1].tolist(), SECOND_ROW)
        self.assertEqual(batch.labels[:3], [0, 1, 0])
        self.assertEqual(sum(batch.labels), 300)

    def test_the_sample_file_is_read(self):
        df = pd.read_csv(SAMPLE, encoding='unicode_escape')
        self.assertEqual(PredictionValidator.validate_csv_structure(df), (True, ''))
        batch = self.preprocessor.prepare_batch(df)
        self.assertEqual(batch.matrix.shape, (len(df), 20))
        self.assertEqual(batch.errors, {})

    def test_missing_columns_are_named(self):
        df = pd.read_csv(DATASET, encoding='unicode_escape').drop(columns=['purpose', 'housing'])
        ok, message = PredictionValidator.validate_csv_structure(df)
        self.assertFalse(ok)
        self.assertEqual(message, 'The file is missing these columns: purpose, housing.')

    def test_one_missing_column_reads_as_singular(self):
        df = pd.read_csv(DATASET, encoding='unicode_escape').drop(columns=['job'])
        self.assertEqual(PredictionValidator.validate_csv_structure(df),
                         (False, 'The file is missing this column: job.'))

    def test_a_header_only_file_is_rejected(self):
        df = pd.read_csv(DATASET, encoding='unicode_escape').head(0)
        ok, message = PredictionValidator.validate_csv_structure(df)
        self.assertFalse(ok)
        self.assertIn('no rows', message)

    def test_files_without_labels_have_none(self):
        df = pd.read_csv(DATASET, encoding='unicode_escape').drop(columns=['class']).head(5)
        batch = self.preprocessor.prepare_batch(df)
        self.assertIsNone(batch.labels)
        self.assertEqual(batch.matrix.shape, (5, 20))

    def test_extra_columns_and_column_order_do_not_matter(self):
        df = pd.read_csv(DATASET, encoding='unicode_escape').head(3)
        df.insert(0, 'Id', [101, 102, 103])
        df = df[list(reversed(df.columns))]
        batch = self.preprocessor.prepare_batch(df)
        self.assertEqual(batch.matrix[0].tolist(), FIRST_ROW)

    def test_rows_that_cannot_be_read_are_set_aside(self):
        df = pd.read_csv(DATASET, encoding='unicode_escape').head(4)
        df['purpose'] = df['purpose'].astype(object)
        df.loc[1, 'purpose'] = 'spaceship'
        df.loc[2, 'cc_age'] = 500

        batch = self.preprocessor.prepare_batch(df)

        self.assertEqual(batch.positions, [0, 3])
        self.assertEqual(batch.matrix.shape, (2, 20))
        self.assertEqual(batch.errors[1], 'Choose one of the listed options for purpose.')
        self.assertEqual(batch.errors[2], 'Age must be between 18 and 100 years.')

    def test_already_encoded_files_are_accepted(self):
        df = pd.DataFrame([dict(zip(FEATURE_NAMES, SECOND_ROW))])
        batch = self.preprocessor.prepare_batch(df)
        self.assertEqual(batch.matrix[0].tolist(), SECOND_ROW)
        self.assertTrue(np.issubdtype(batch.matrix.dtype, np.floating))


if __name__ == '__main__':
    unittest.main()
