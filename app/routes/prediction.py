from flask import Blueprint, render_template, request, jsonify
import logging
from app.utils.decorators import login_required
from app.utils.validators import PredictionValidator
from app.utils.schema import GROUPS, features_in_group
from app.models.fraud_model import ModelUnavailable, get_model

logger = logging.getLogger(__name__)

bp = Blueprint('prediction', __name__, url_prefix='/')

# Two applications from the held-out test rows of data/credit_data.csv (file
# rows 87 and 833), one of each class, offered as worked examples. Values are
# the codes from app.utils.schema.
EXAMPLES = (
    {
        'key': 'low',
        'label': 'Low-risk example',
        'values': {
            'over_draft': 4, 'credit_usage': 12, 'credit_history': 5, 'purpose': 9,
            'current_balance': 1412, 'average_credit_balance': 2, 'employment': 3, 'location': 4,
            'personal_status': 4, 'other_parties': 3, 'residence_since': 2, 'property_magnitude': 1,
            'cc_age': 29, 'other_payment_plans': 1, 'housing': 1, 'existing_credits': 2, 'job': 4,
            'num_dependents': 1, 'own_telephone': 1, 'foreign_worker': 1,
        },
    },
    {
        'key': 'high',
        'label': 'High-risk example',
        'values': {
            'over_draft': 1, 'credit_usage': 18, 'credit_history': 3, 'purpose': 1,
            'current_balance': 1216, 'average_credit_balance': 2, 'employment': 2, 'location': 4,
            'personal_status': 4, 'other_parties': 1, 'residence_since': 3, 'property_magnitude': 3,
            'cc_age': 23, 'other_payment_plans': 1, 'housing': 2, 'existing_credits': 1, 'job': 3,
            'num_dependents': 1, 'own_telephone': 1, 'foreign_worker': 1,
        },
    },
)


def _wants_json():
    """True when the page's own script asks for the result as JSON"""
    accept = request.accept_mimetypes
    return accept['application/json'] > accept['text/html']


def _form_groups():
    return [
        {'key': key, 'title': title, 'description': description, 'features': features_in_group(key)}
        for key, title, description, _ in GROUPS
    ]


def _render(status=200, **context):
    return render_template(
        'prediction.html',
        groups=_form_groups(),
        examples=EXAMPLES,
        **context,
    ), status


@bp.route('/prediction', methods=['GET', 'POST'])
@login_required
def prediction():
    """Single-application prediction page"""
    if request.method == 'GET':
        return _render(features={}, errors={})

    features_dict = request.form.to_dict()
    values, errors = PredictionValidator.parse_features(features_dict)

    if errors:
        logger.warning(f"Validation failed: {errors}")
        if _wants_json():
            # A mistyped field is an expected outcome for the page script, not a
            # failed request, so it travels in the body with a normal status.
            return jsonify({'ok': False, 'errors': errors})
        # List the problems in the order the form shows the fields.
        ordered = [
            {'name': feature.name, 'label': feature.label, 'message': errors[feature.name]}
            for key, _, _, _ in GROUPS for feature in features_in_group(key)
            if feature.name in errors
        ]
        return _render(400, features=features_dict, errors=errors, error_list=ordered)

    try:
        result = get_model().predict(values)
    except ModelUnavailable as e:
        logger.error(f"Prediction unavailable: {str(e)}")
        if _wants_json():
            return jsonify({'ok': False, 'message': str(e)}), 503
        return _render(503, features=features_dict, errors={}, problem=str(e))

    logger.info(f"Prediction successful: {result}")
    if _wants_json():
        return jsonify({'ok': True, 'result': result})
    return _render(features=features_dict, errors={}, prediction_result=result)

