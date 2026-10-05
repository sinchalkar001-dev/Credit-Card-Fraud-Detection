import os
import unittest

import pandas as pd

from app.utils.schema import (FEATURES, FEATURE_NAMES, FEATURES_BY_NAME, GROUPS, TARGET_CODES,
                              TARGET_COLUMN, describe_features, features_in_group)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET = os.path.join(ROOT, 'data', 'credit_data.csv')


def dataset():
    df = pd.read_csv(DATASET, encoding='unicode_escape')
    df.columns = [str(column).strip().lower() for column in df.columns]
    return df


class FeatureSchemaTest(unittest.TestCase):
    def test_features_are_the_dataset_columns_in_order(self):
        columns = [column for column in dataset().columns if column != TARGET_COLUMN]
        self.assertEqual(list(FEATURE_NAMES), columns)
        self.assertEqual(len(FEATURE_NAMES), 20)

    def test_every_value_in_the_dataset_has_a_code(self):
        df = dataset()
        for feature in FEATURES:
            if feature.kind != 'choice':
                continue
            with self.subTest(feature=feature.name):
                known = {choice.raw.lower() for choice in feature.choices}
                found = set(df[feature.name].astype(str).str.strip().str.lower().unique())
                self.assertEqual(found - known, set())

    def test_every_choice_occurs_in_the_dataset(self):
        df = dataset()
        for feature in FEATURES:
            if feature.kind != 'choice':
                continue
            with self.subTest(feature=feature.name):
                known = {choice.raw.lower() for choice in feature.choices}
                found = set(df[feature.name].astype(str).str.strip().str.lower().unique())
                self.assertEqual(known - found, set())

    def test_codes_count_up_from_one(self):
        for feature in FEATURES:
            if feature.kind == 'choice':
                with self.subTest(feature=feature.name):
                    codes = [choice.code for choice in feature.choices]
                    self.assertEqual(codes, list(range(1, len(codes) + 1)))

    def test_ordered_values_are_coded_in_their_natural_order(self):
        raw = lambda name: [choice.raw for choice in FEATURES_BY_NAME[name].choices]
        self.assertEqual(raw('average_credit_balance'),
                         ['no known savings', '<100', '100<=X<500', '500<=X<1000', '>=1000'])
        self.assertEqual(raw('employment'), ['unemployed', '<1', '1<=X<4', '4<=X<7', '>=7'])
        self.assertEqual(raw('over_draft'), ['<0', '0<=X<200', '>=200', 'no checking'])
        self.assertEqual(raw('location'), ['1', '2', '3', '4'])

    def test_number_features_have_a_range_that_covers_the_dataset(self):
        df = dataset()
        for feature in FEATURES:
            if feature.kind == 'number':
                with self.subTest(feature=feature.name):
                    self.assertLessEqual(feature.minimum, df[feature.name].min())
                    self.assertGreaterEqual(feature.maximum, df[feature.name].max())

    def test_form_groups_hold_every_feature_once(self):
        grouped = [feature.name for key, _, _, _ in GROUPS for feature in features_in_group(key)]
        self.assertEqual(sorted(grouped), sorted(FEATURE_NAMES))

    def test_the_target_column_holds_only_known_labels(self):
        labels = set(dataset()[TARGET_COLUMN].str.strip().str.lower().unique())
        self.assertEqual(labels, set(TARGET_CODES))

    def test_description_for_the_api_lists_choices_and_ranges(self):
        described = describe_features()
        self.assertEqual(list(described), list(FEATURE_NAMES))
        self.assertEqual(described['cc_age']['minimum'], 18)
        self.assertEqual(described['housing']['choices'][0], {'code': 1, 'value': 'own', 'label': 'Own'})


if __name__ == '__main__':
    unittest.main()
