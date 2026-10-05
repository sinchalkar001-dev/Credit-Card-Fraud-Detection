import io
import os
import re
import unittest

from app import create_app
from app.routes.prediction import EXAMPLES
from app.utils.insights import load_model_info
from app.utils.schema import FEATURE_NAMES
from tests.test_validators import VALID_RAW

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET = os.path.join(ROOT, 'data', 'credit_data.csv')

EXAMPLE = {example['key']: {k: str(v) for k, v in example['values'].items()} for example in EXAMPLES}
AS_JSON = {'Accept': 'application/json'}


def upload(content, filename='rows.csv'):
    return {'datasetfile': (io.BytesIO(content), filename)}


def dataset_lines(count):
    """The header and the first `count` rows of the bundled dataset."""
    with open(DATASET, 'rb') as f:
        return f.readlines()[:count + 1]


class RouteTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app('testing')

    def setUp(self):
        self.client = self.app.test_client()

    def login(self, **kwargs):
        credentials = {
            'username': self.app.config['ADMIN_USERNAME'],
            'password': self.app.config['ADMIN_PASSWORD'],
        }
        return self.client.post('/login', data=credentials, **kwargs)


class PublicPagesTest(RouteTestCase):
    def test_home_page_renders_for_visitors(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Sign in', response.data)

    def test_home_page_renders_when_signed_in(self):
        self.login()
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'href="/prediction"', response.data)

    def test_protected_pages_send_visitors_to_sign_in_and_back(self):
        for path in ('/prediction', '/upload', '/chart', '/performance'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.headers['Location'], f'/login?next={path}')

    def test_unknown_page_is_a_readable_404(self):
        response = self.client.get('/no-such-page')
        self.assertEqual(response.status_code, 404)
        self.assertIn('text/html', response.content_type)
        self.assertIn(b'This page does not exist', response.data)

    def test_unknown_api_path_is_a_json_404(self):
        response = self.client.get('/api/no-such-endpoint')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()['error'], 'This page does not exist')

    def test_responses_carry_security_headers(self):
        response = self.client.get('/')
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response.headers['X-Frame-Options'], 'DENY')
        self.assertIn("script-src 'self'", response.headers['Content-Security-Policy'])

    def test_scripts_and_styles_are_served_with_types_browsers_accept(self):
        for path, expected in (('/static/js/app.js', 'text/javascript'),
                               ('/static/css/tokens.css', 'text/css'),
                               ('/static/img/favicon.svg', 'image/svg+xml'),
                               ('/static/fonts/ibm-plex-sans-latin-var.woff2', 'font/woff2')):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn(expected, response.content_type)
                response.close()


class SignInTest(RouteTestCase):
    def test_sign_in_page_renders(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'name="username"', response.data)
        self.assertIn(b'name="password"', response.data)

    def test_wrong_password_is_refused_and_the_username_kept(self):
        response = self.client.post('/login', data={'username': 'admin', 'password': 'nope'})
        self.assertEqual(response.status_code, 401)
        self.assertIn(b'do not match', response.data)
        self.assertIn(b'value="admin"', response.data)
        self.assertEqual(self.client.get('/prediction').status_code, 302)

    def test_both_fields_are_required(self):
        response = self.client.post('/login', data={'username': 'admin', 'password': ''})
        self.assertEqual(response.status_code, 401)
        self.assertIn(b'Enter both', response.data)

    def test_sign_in_opens_the_home_page(self):
        response = self.login()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/')

    def test_sign_in_returns_to_the_page_that_was_asked_for(self):
        response = self.login(query_string={'next': '/chart'})
        self.assertEqual(response.headers['Location'], '/chart')

    def test_sign_in_never_redirects_off_site(self):
        for target in ('//evil.example', 'https://evil.example', '/\\evil.example'):
            with self.subTest(target=target):
                response = self.login(query_string={'next': target})
                self.assertEqual(response.headers['Location'], '/')
                self.client.get('/logout')

    def test_sign_out_ends_the_session(self):
        self.login()
        self.assertEqual(self.client.get('/prediction').status_code, 200)
        response = self.client.post('/logout')
        self.assertEqual(response.headers['Location'], '/login')
        self.assertEqual(self.client.get('/prediction').status_code, 302)


class PredictionTest(RouteTestCase):
    def setUp(self):
        super().setUp()
        self.login()

    def test_blank_form_renders_every_model_input(self):
        response = self.client.get('/prediction')
        self.assertEqual(response.status_code, 200)
        for name in FEATURE_NAMES:
            with self.subTest(field=name):
                self.assertIn(f'name="{name}"'.encode(), response.data)

    def test_low_risk_example_is_cleared(self):
        response = self.client.post('/prediction', data=EXAMPLE['low'], headers=AS_JSON)
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body['ok'])
        self.assertEqual(body['result']['prediction'], 'good')
        self.assertFalse(body['result']['flagged'])

    def test_high_risk_example_is_flagged(self):
        response = self.client.post('/prediction', data=EXAMPLE['high'], headers=AS_JSON)
        body = response.get_json()
        self.assertEqual(body['result']['prediction'], 'bad')
        self.assertTrue(body['result']['flagged'])
        self.assertGreater(body['result']['risk_score'], 50)

    def test_result_is_rendered_without_javascript(self):
        response = self.client.post('/prediction', data=EXAMPLE['high'])
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'data-verdict="flagged"', response.data)
        self.assertIn(b'Flagged as high risk', response.data)
        # The submitted values are still in the form.
        self.assertIn(b'value="1216"', response.data)

    def test_problems_are_listed_next_to_their_fields(self):
        data = dict(EXAMPLE['high'], cc_age='140', purpose='')
        response = self.client.post('/prediction', data=data)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Fix 2 fields to get a verdict', response.data)
        self.assertIn(b'Age must be between 18 and 100 years.', response.data)
        self.assertIn(b'Choose an option for purpose.', response.data)
        self.assertIn(b'aria-invalid="true"', response.data)
        self.assertNotIn(b'data-verdict=', response.data)

    def test_problems_come_back_as_json_for_the_page_script(self):
        data = dict(EXAMPLE['high'], cc_age='140')
        response = self.client.post('/prediction', data=data, headers=AS_JSON)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {
            'ok': False,
            'errors': {'cc_age': 'Age must be between 18 and 100 years.'},
        })


class UploadTest(RouteTestCase):
    def setUp(self):
        super().setUp()
        self.login()

    def test_upload_page_names_the_columns_it_needs(self):
        response = self.client.get('/upload')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'name="datasetfile"', response.data)
        for name in FEATURE_NAMES:
            with self.subTest(column=name):
                self.assertIn(f'<code>{name}</code>'.encode(), response.data)

    def test_bundled_dataset_is_scored(self):
        with open(DATASET, 'rb') as f:
            response = self.client.post('/preview', data=upload(f.read(), 'credit data.csv'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Results for credit_data.csv', response.data)
        self.assertIn(b'1,000 of 1,000 rows scored', response.data)
        self.assertEqual(response.data.count(b'<tr data-row '), 1000)

    def test_excel_style_csv_with_a_byte_order_mark_is_scored(self):
        content = b'\xef\xbb\xbf' + b''.join(dataset_lines(5))
        response = self.client.post('/preview', data=upload(content))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'5 of 5 rows scored', response.data)

    def test_file_without_labels_is_scored(self):
        header = ','.join(FEATURE_NAMES)
        row = ','.join(EXAMPLE['high'][name] for name in FEATURE_NAMES)
        response = self.client.post('/preview', data=upload(f'{header}\n{row}\n'.encode()))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'1 of 1 row scored', response.data)
        self.assertNotIn(b'Your label', response.data)

    def test_capitalised_none_is_read_as_the_word_not_as_a_blank(self):
        lines = dataset_lines(2)
        lines[1] = lines[1].replace(b',none,', b',None,')
        response = self.client.post('/preview', data=upload(b''.join(lines)))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'2 of 2 rows scored', response.data)

    def test_other_file_types_are_refused(self):
        response = self.client.post('/preview', data=upload(b'PK\x03\x04', 'rows.xlsx'))
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Only CSV files can be scored', response.data)

    def test_missing_columns_are_named(self):
        response = self.client.post('/preview', data=upload(b'credit_usage,purpose\n6,radio/tv\n'))
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'The file is missing these columns', response.data)
        self.assertIn(b'current_balance', response.data)

    def test_no_file_is_reported(self):
        response = self.client.post('/preview', data={})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Choose a CSV file to score.', response.data)

    def test_empty_file_is_reported(self):
        response = self.client.post('/preview', data=upload(b''))
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'The file is empty', response.data)

    def test_too_many_rows_are_refused(self):
        lines = dataset_lines(3)
        limit = self.app.config['MAX_BATCH_ROWS']
        self.app.config['MAX_BATCH_ROWS'] = 2
        try:
            response = self.client.post('/preview', data=upload(b''.join(lines)))
        finally:
            self.app.config['MAX_BATCH_ROWS'] = limit
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'The file has 3 rows', response.data)

    def test_rows_that_cannot_be_read_do_not_stop_the_rest(self):
        lines = dataset_lines(3)
        lines[2] = lines[2].replace(b'radio/tv', b'spaceship')
        response = self.client.post('/preview', data=upload(b''.join(lines)))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'2 of 3 rows scored', response.data)
        self.assertIn(b'Choose one of the listed options for purpose.', response.data)

    def test_sample_file_downloads_and_can_be_scored(self):
        response = self.client.get('/upload/sample')
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response.content_type)
        self.assertIn('attachment', response.headers['Content-Disposition'])
        sample = response.data
        response.close()

        scored = self.client.post('/preview', data=upload(sample, 'sample-applications.csv'))
        self.assertEqual(scored.status_code, 200)
        self.assertIn(b'12 of 12 rows scored', scored.data)

    def test_results_address_without_a_file_returns_to_upload(self):
        response = self.client.get('/preview')
        self.assertEqual(response.headers['Location'], '/upload')


class InsightPagesTest(RouteTestCase):
    def setUp(self):
        super().setUp()
        self.login()

    def test_analytics_shows_the_real_class_balance(self):
        response = self.client.get('/chart')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'1,000', response.data)
        self.assertIn(b'data-count="300"', response.data)
        self.assertIn(b'data-count="700"', response.data)
        # The old page reported an invented 10,000 rows.
        self.assertNotIn(b'10,000', response.data)

    def test_analytics_offers_every_model_input_as_a_breakdown(self):
        response = self.client.get('/chart')
        for name in FEATURE_NAMES:
            with self.subTest(dimension=name):
                self.assertIn(f'<option value="{name}"'.encode(), response.data)

    def test_performance_shows_the_recorded_scores(self):
        info = load_model_info(self.app.config['MODEL_INFO_PATH'])
        test = info['evaluations'][info['serving']]['test']

        response = self.client.get('/performance')
        self.assertEqual(response.status_code, 200)
        self.assertIn(f"{test['roc_auc']:.3f}".encode(), response.data)
        self.assertIn(f"{test['recall'] * 100:.1f}".encode(), response.data)
        self.assertIn(f"{test['accuracy'] * 100:.1f}".encode(), response.data)
        self.assertIn(f">{test['confusion_matrix']['tp']}<".encode(), response.data)
        self.assertIn(b'Gradient Boosting', response.data)


class ApiTest(RouteTestCase):
    def test_health(self):
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['status'], 'healthy')

    def test_predict_with_dataset_wording(self):
        response = self.client.post('/api/predict', json=VALID_RAW)
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body['success'])
        self.assertEqual(set(body['prediction']), {'prediction', 'flagged', 'risk_score'})
        self.assertIn(body['prediction']['prediction'], ('good', 'bad'))

    def test_predict_with_codes_gives_the_same_answer_as_the_form(self):
        codes = {name: int(value) for name, value in EXAMPLE['high'].items()}
        response = self.client.post('/api/predict', json=codes)
        self.assertEqual(response.get_json()['prediction']['prediction'], 'bad')

    def test_predict_names_the_fields_that_need_fixing(self):
        response = self.client.post('/api/predict', json={'credit_usage': 48})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(response.get_json()['fields']), 19)

    def test_predict_needs_a_json_body(self):
        response = self.client.post('/api/predict', data='not json')
        self.assertEqual(response.status_code, 400)

    def test_predict_batch(self):
        response = self.client.post(
            '/api/predict-batch', data={'file': (io.BytesIO(b''.join(dataset_lines(5))), 'rows.csv')})
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body['total_records'], 5)
        self.assertEqual([row['row'] for row in body['results']], [1, 2, 3, 4, 5])
        self.assertIn(body['results'][0]['prediction']['prediction'], ('good', 'bad'))

    def test_model_info_lists_the_twenty_inputs(self):
        body = self.client.get('/api/model-info').get_json()
        self.assertEqual(body['model']['expected_features'], 20)
        self.assertEqual(body['model']['features'], list(FEATURE_NAMES))
        self.assertIn('choices', body['model']['descriptions']['purpose'])
        self.assertIn('roc_auc', body['model']['test_scores'])


class CsrfTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app.config['CSRF_ENABLED'] = True
        self.client = self.app.test_client()
        self.credentials = {
            'username': self.app.config['ADMIN_USERNAME'],
            'password': self.app.config['ADMIN_PASSWORD'],
        }

    def token(self):
        page = self.client.get('/login').get_data(as_text=True)
        return re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)

    def test_form_post_without_the_token_is_refused(self):
        response = self.client.post('/login', data=self.credentials)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'This form expired', response.data)

    def test_form_post_with_the_token_is_accepted(self):
        response = self.client.post('/login', data=dict(self.credentials, csrf_token=self.token()))
        self.assertEqual(response.status_code, 302)

    def test_token_from_another_session_is_refused(self):
        token = self.token()
        other = self.app.test_client()
        other.get('/login')
        response = other.post('/login', data=dict(self.credentials, csrf_token=token))
        self.assertEqual(response.status_code, 400)

    def test_refusal_comes_back_as_json_for_the_page_script(self):
        response = self.client.post('/login', data=self.credentials, headers=AS_JSON)
        self.assertEqual(response.status_code, 400)
        self.assertIn('This form expired', response.get_json()['detail'])

    def test_api_does_not_need_the_token(self):
        response = self.client.post('/api/predict', json={'credit_usage': 48})
        self.assertEqual(response.status_code, 400)
        self.assertIn('fields', response.get_json())


if __name__ == '__main__':
    unittest.main()
