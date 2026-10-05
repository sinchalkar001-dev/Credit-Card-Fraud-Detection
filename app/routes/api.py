from flask import Blueprint, current_app, request, jsonify
import logging
import pandas as pd
from app.utils.validators import FileValidator, PredictionValidator
from app.utils.preprocessing import DataPreprocessor
from app.utils.insights import load_model_info
from app.models.fraud_model import ModelUnavailable, get_model

logger = logging.getLogger(__name__)

bp = Blueprint('api', __name__, url_prefix='/api')
preprocessor = DataPreprocessor()


@bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'API is running'
    }), 200


@bp.route('/predict', methods=['POST'])
def predict():
    """
    Classify a single application

    Request JSON holds the 20 model inputs. Choice fields take the dataset
    wording, the label or the model code (see GET /api/model-info):
    {
        "over_draft": "<0",
        "credit_usage": 18,
        "purpose": "new car",
        ...
    }

    Response: {"success": true, "prediction": {"prediction": "bad",
    "flagged": true, "risk_score": 92.5}}
    """
    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    values, errors = PredictionValidator.parse_features(data)
    if errors:
        return jsonify({'error': 'Some values are missing or cannot be used.', 'fields': errors}), 400

    try:
        result = get_model().predict(values)
    except ModelUnavailable as e:
        return jsonify({'error': str(e)}), 503
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        return jsonify({'error': 'The prediction could not be made.'}), 500

    logger.info(f"API prediction: {result}")
    return jsonify({
        'success': True,
        'prediction': result
    }), 200


@bp.route('/predict-batch', methods=['POST'])
def predict_batch():
    """
    Classify every row of a CSV file

    Request: CSV file upload (form field "file") with the model's feature columns
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not FileValidator.allowed_file(file.filename):
        return jsonify({'error': 'Only CSV files allowed'}), 400

    try:
        df = preprocessor.read_csv(file)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as e:
        return jsonify({'error': f"CSV parsing error: {str(e)}"}), 400

    is_valid_csv, csv_error = PredictionValidator.validate_csv_structure(df)
    if not is_valid_csv:
        return jsonify({'error': csv_error}), 400

    max_rows = current_app.config['MAX_BATCH_ROWS']
    if len(df) > max_rows:
        return jsonify({'error': f'The file has {len(df)} rows; the limit is {max_rows}.'}), 400

    try:
        batch = preprocessor.prepare_batch(df)
        predictions = dict(zip(batch.positions, get_model().predict_many(batch.matrix)))
    except ModelUnavailable as e:
        return jsonify({'error': str(e)}), 503
    except Exception as e:
        logger.error(f"Batch prediction error: {str(e)}")
        return jsonify({'error': 'The file could not be scored.'}), 500

    results = []
    for position in range(len(df)):
        if position in predictions:
            results.append({'row': position + 1, 'prediction': predictions[position]})
        else:
            results.append({'row': position + 1, 'error': batch.errors[position]})

    logger.info(f"Batch prediction completed for {len(df)} records")
    return jsonify({
        'success': True,
        'total_records': len(df),
        'results': results
    }), 200


@bp.route('/model-info', methods=['GET'])
def model_info():
    """Get model information and expected features"""
    info = get_model().get_model_info()
    recorded = load_model_info(current_app.config['MODEL_INFO_PATH']) or {}
    serving = recorded.get('evaluations', {}).get(recorded.get('serving'), {})

    return jsonify({
        'success': True,
        'model': {
            'algorithm': recorded.get('algorithm'),
            'params': recorded.get('params'),
            'trained_at': recorded.get('trained_at'),
            'expected_features': info['expected_features'],
            'features': info['feature_names'],
            'descriptions': DataPreprocessor.get_feature_description(),
            'baseline_accuracy': recorded.get('baseline_accuracy'),
            'test_scores': serving.get('test'),
            'cross_validation': serving.get('cross_validation'),
        }
    }), 200
