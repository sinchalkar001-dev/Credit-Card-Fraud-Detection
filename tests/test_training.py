"""The scores the app shows must be the ones the saved model actually earns."""

import json
import pickle
import unittest

import numpy as np
from sklearn.model_selection import train_test_split

import train_model
from app.utils.schema import FEATURE_NAMES


class RecordedScoresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(train_model.MODEL_INFO_PATH, encoding='utf-8') as f:
            cls.info = json.load(f)
        with open(train_model.MODEL_PATH, 'rb') as f:
            cls.model = pickle.load(f)

        cls.X, cls.y = train_model.load_dataset()
        rows = np.arange(len(cls.y))
        cls.train_rows, cls.test_rows = train_test_split(
            rows, test_size=train_model.TEST_SIZE, stratify=cls.y, random_state=train_model.SEED)

    def test_the_test_rows_are_held_out_before_anything_else(self):
        self.assertEqual(set(self.train_rows) & set(self.test_rows), set())
        self.assertEqual(self.info['split']['train_rows'], len(self.train_rows))
        self.assertEqual(self.info['split']['test_rows'], len(self.test_rows))
        self.assertEqual(len(self.test_rows), 200)

    def test_no_held_out_application_is_a_copy_of_a_training_one(self):
        seen = {tuple(row) for row in self.X[self.train_rows]}
        copies = [row for row in self.X[self.test_rows] if tuple(row) in seen]
        self.assertEqual(copies, [])

    def test_the_split_keeps_the_class_mix(self):
        self.assertAlmostEqual(self.y[self.test_rows].mean(), 0.3)
        self.assertAlmostEqual(self.y[self.train_rows].mean(), 0.3)
        self.assertAlmostEqual(self.info['baseline_accuracy'], 0.7)

    def test_recorded_scores_are_what_the_saved_model_earns(self):
        fresh = train_model.score(self.model, self.X[self.test_rows], self.y[self.test_rows])
        recorded = self.info['evaluations'][self.info['serving']]['test']
        for metric in train_model.METRICS:
            with self.subTest(metric=metric):
                self.assertAlmostEqual(fresh[metric], recorded[metric], places=9)
        self.assertEqual(fresh['confusion_matrix'], recorded['confusion_matrix'])

    def test_the_confusion_matrix_counts_every_held_out_row_once(self):
        for name, evaluation in self.info['evaluations'].items():
            with self.subTest(model=name):
                matrix = evaluation['test']['confusion_matrix']
                self.assertEqual(sum(matrix.values()), len(self.test_rows))
                self.assertEqual(matrix['fn'] + matrix['tp'], int(self.y[self.test_rows].sum()))

    def test_the_model_beats_guessing(self):
        test = self.info['evaluations'][self.info['serving']]['test']
        self.assertGreater(test['roc_auc'], 0.7)
        self.assertGreater(test['accuracy'], self.info['baseline_accuracy'])

    def test_the_weighted_model_catches_more_bad_applications(self):
        weighted = self.info['evaluations']['weighted']['test']
        unweighted = self.info['evaluations']['unweighted']['test']
        self.assertGreater(weighted['recall'], unweighted['recall'])

    def test_both_models_were_cross_validated(self):
        for name, evaluation in self.info['evaluations'].items():
            for metric in train_model.METRICS:
                with self.subTest(model=name, metric=metric):
                    fold = evaluation['cross_validation'][metric]
                    self.assertTrue(0 <= fold['mean'] <= 1)
                    self.assertGreaterEqual(fold['std'], 0)

    def test_importances_cover_every_input(self):
        names = [item['feature'] for item in self.info['feature_importances']]
        self.assertEqual(sorted(names), sorted(FEATURE_NAMES))
        self.assertAlmostEqual(sum(item['importance'] for item in self.info['feature_importances']), 1.0)

    def test_artifacts_are_recognised_as_ready(self):
        self.assertTrue(train_model.artifacts_ready())


if __name__ == '__main__':
    unittest.main()
