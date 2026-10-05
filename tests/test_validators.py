import unittest

from app.utils.validators import FileValidator, PredictionValidator

# First row of data/credit_data.csv, as the form posts it (codes).
VALID_CODES = {
    'over_draft': '1', 'credit_usage': '6', 'credit_history': '5', 'purpose': '4',
    'current_balance': '1169', 'average_credit_balance': '1', 'employment': '5', 'location': '4',
    'personal_status': '1', 'other_parties': '1', 'residence_since': '4', 'property_magnitude': '1',
    'cc_age': '67', 'other_payment_plans': '1', 'housing': '1', 'existing_credits': '2', 'job': '3',
    'num_dependents': '1', 'own_telephone': '1', 'foreign_worker': '1',
}

# The same row as it is written in the dataset.
VALID_RAW = {
    'over_draft': '<0', 'credit_usage': 6, 'credit_history': 'critical/other existing credit',
    'purpose': 'radio/tv', 'current_balance': 1169, 'average_credit_balance': 'no known savings',
    'employment': '>=7', 'location': 4, 'personal_status': 'male single', 'other_parties': 'none',
    'residence_since': 4, 'property_magnitude': 'real estate', 'cc_age': 67,
    'other_payment_plans': 'none', 'housing': 'own', 'existing_credits': 2, 'job': 'skilled',
    'num_dependents': 1, 'own_telephone': 'yes', 'foreign_worker': 'yes',
}

EXPECTED_VECTOR = [1.0, 6.0, 5.0, 4.0, 1169.0, 1.0, 5.0, 4.0, 1.0, 1.0,
                   4.0, 1.0, 67.0, 1.0, 1.0, 2.0, 3.0, 1.0, 1.0, 1.0]


class ParseFeaturesTest(unittest.TestCase):
    def test_form_codes_become_the_model_vector(self):
        vector, errors = PredictionValidator.parse_features(VALID_CODES)
        self.assertEqual(errors, {})
        self.assertEqual(vector, EXPECTED_VECTOR)

    def test_dataset_wording_is_accepted(self):
        vector, errors = PredictionValidator.parse_features(VALID_RAW)
        self.assertEqual(errors, {})
        self.assertEqual(vector, EXPECTED_VECTOR)

    def test_interface_labels_are_accepted(self):
        data = dict(VALID_RAW, over_draft='Overdrawn', employment='7 years or more', own_telephone='Yes')
        vector, errors = PredictionValidator.parse_features(data)
        self.assertEqual(errors, {})
        self.assertEqual(vector, EXPECTED_VECTOR)

    def test_wording_is_matched_without_regard_to_case_or_padding(self):
        data = dict(VALID_RAW, purpose='  Radio/TV ', housing='OWN')
        vector, errors = PredictionValidator.parse_features(data)
        self.assertEqual(errors, {})
        self.assertEqual(vector, EXPECTED_VECTOR)

    def test_every_missing_field_is_reported(self):
        vector, errors = PredictionValidator.parse_features({'credit_usage': '6'})
        self.assertIsNone(vector)
        self.assertEqual(len(errors), 19)
        self.assertNotIn('credit_usage', errors)
        self.assertEqual(errors['current_balance'], 'Enter current balance.')
        self.assertEqual(errors['purpose'], 'Choose an option for purpose.')

    def test_blank_values_count_as_missing(self):
        _, errors = PredictionValidator.parse_features(dict(VALID_CODES, cc_age='  '))
        self.assertEqual(errors, {'cc_age': 'Enter age.'})

    def test_numbers_outside_the_range_are_rejected(self):
        _, errors = PredictionValidator.parse_features(dict(VALID_CODES, cc_age='140'))
        self.assertEqual(errors, {'cc_age': 'Age must be between 18 and 100 years.'})

    def test_large_ranges_are_written_with_separators(self):
        _, errors = PredictionValidator.parse_features(dict(VALID_CODES, current_balance='-5'))
        self.assertEqual(
            errors, {'current_balance': 'Current balance must be between 0 and 1,000,000.'})

    def test_text_in_a_number_field_is_rejected(self):
        _, errors = PredictionValidator.parse_features(dict(VALID_CODES, current_balance='lots'))
        self.assertEqual(errors, {'current_balance': 'Current balance must be a number.'})

    def test_not_a_number_values_are_rejected(self):
        for value in ('nan', 'inf', float('nan'), True):
            with self.subTest(value=value):
                _, errors = PredictionValidator.parse_features(
                    dict(VALID_CODES, current_balance=value))
                self.assertIn('current_balance', errors)

    def test_whole_number_fields_reject_fractions(self):
        _, errors = PredictionValidator.parse_features(dict(VALID_CODES, credit_usage='6.5'))
        self.assertEqual(errors, {'credit_usage': 'Credit usage must be a whole number.'})

    def test_unknown_choices_are_rejected(self):
        for value in ('0', '99', 'spaceship'):
            with self.subTest(value=value):
                _, errors = PredictionValidator.parse_features(dict(VALID_CODES, purpose=value))
                self.assertEqual(
                    errors, {'purpose': 'Choose one of the listed options for purpose.'})

    def test_a_scale_only_takes_its_own_steps(self):
        _, errors = PredictionValidator.parse_features(dict(VALID_CODES, location='5'))
        self.assertEqual(errors, {'location': 'Choose one of the listed options for location.'})

    def test_fields_the_model_does_not_use_are_ignored(self):
        data = dict(VALID_CODES, csrf_token='abc', note='call back on Friday')
        vector, errors = PredictionValidator.parse_features(data)
        self.assertEqual(errors, {})
        self.assertEqual(vector, EXPECTED_VECTOR)

    def test_validate_features_summarises_the_first_problem(self):
        self.assertEqual(PredictionValidator.validate_features(VALID_CODES), (True, ''))
        ok, message = PredictionValidator.validate_features(dict(VALID_CODES, cc_age='140'))
        self.assertFalse(ok)
        self.assertEqual(message, 'Age must be between 18 and 100 years.')


class FileValidatorTest(unittest.TestCase):
    def test_only_csv_files_are_allowed(self):
        self.assertEqual(FileValidator.validate_file('rows.csv', 10), (True, ''))
        self.assertEqual(FileValidator.validate_file('ROWS.CSV', 10), (True, ''))
        ok, message = FileValidator.validate_file('rows.xlsx', 10)
        self.assertFalse(ok)
        self.assertIn('CSV', message)

    def test_empty_files_are_rejected(self):
        ok, message = FileValidator.validate_file('rows.csv', 0)
        self.assertFalse(ok)
        self.assertIn('empty', message)

    def test_oversized_files_are_rejected(self):
        ok, message = FileValidator.validate_file('rows.csv', FileValidator.MAX_FILE_SIZE + 1)
        self.assertFalse(ok)
        self.assertIn('16 MB', message)


if __name__ == '__main__':
    unittest.main()
