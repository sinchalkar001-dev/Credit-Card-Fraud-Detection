import pickle
import threading
import numpy as np
import logging
from typing import Dict, Any, List, Sequence

from app.utils.schema import FEATURE_NAMES, TARGET_LABELS

logger = logging.getLogger(__name__)


class ModelUnavailable(RuntimeError):
    """The model file is missing or cannot be loaded in this environment"""


class FraudDetectionModel:
    """Wrapper for the credit-risk ML model with caching and validation"""

    _models: Dict[str, Any] = {}
    _lock = threading.Lock()

    def __init__(self, model_path: str):
        self.model_path = model_path
        self.feature_names = list(FEATURE_NAMES)
        self.expected_features = len(self.feature_names)

    def load_model(self):
        """Lazy load model from pickle file"""
        cached = FraudDetectionModel._models.get(self.model_path)
        if cached is not None:
            return cached

        with FraudDetectionModel._lock:
            cached = FraudDetectionModel._models.get(self.model_path)
            if cached is not None:
                return cached

            try:
                with open(self.model_path, 'rb') as f:
                    model = pickle.load(f)
            except FileNotFoundError as e:
                logger.error(f"Model file not found at {self.model_path}")
                raise ModelUnavailable(
                    'The model file is missing. Run "python train_model.py" to create it.') from e
            except Exception as e:
                # A classifier pickled by another scikit-learn version fails here.
                logger.error(f"Error loading model: {str(e)}")
                raise ModelUnavailable(
                    'The model file was saved by a different scikit-learn version. '
                    'Run "python train_model.py" to rebuild it.') from e

            fitted_on = getattr(model, 'n_features_in_', self.expected_features)
            if fitted_on != self.expected_features:
                logger.error(f"Model expects {fitted_on} features, app sends {self.expected_features}")
                raise ModelUnavailable(
                    f'The model file expects {fitted_on} inputs but the app sends '
                    f'{self.expected_features}. Run "python train_model.py" to rebuild it.')

            FraudDetectionModel._models[self.model_path] = model
            logger.info(f"Model loaded successfully from {self.model_path}")
            return model

    def predict(self, features: Sequence[float]) -> Dict[str, Any]:
        """
        Score one application

        Args:
            features: Feature values in model order (see app.utils.schema)

        Returns:
            Dictionary with the predicted class, whether it is flagged and
            the risk score (0-100)
        """
        if len(features) != self.expected_features:
            raise ValueError(f"Expected {self.expected_features} features, got {len(features)}")

        result = self.predict_many(np.array([features], dtype=float))[0]
        logger.info(f"Prediction made: {result['prediction']} (risk score: {result['risk_score']:.1f})")
        return result

    def predict_many(self, matrix: np.ndarray) -> List[Dict[str, Any]]:
        """
        Score many applications at once

        Args:
            matrix: Array of shape (rows, features) in model order

        Returns:
            One prediction dictionary per row
        """
        model = self.load_model()
        if len(matrix) == 0:
            return []

        # The model's probability that an application is bad, as a 0-100 score.
        # Above 50 the application is flagged.
        risk = model.predict_proba(matrix)[:, list(model.classes_).index(1)]
        return [
            {
                'prediction': TARGET_LABELS[int(value > 0.5)],
                'flagged': bool(value > 0.5),
                'risk_score': float(value) * 100,
            }
            for value in risk
        ]

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            'expected_features': self.expected_features,
            'feature_names': self.feature_names,
            'model_path': self.model_path
        }

    @staticmethod
    def reset():
        """Reset the cached model (useful for testing)"""
        with FraudDetectionModel._lock:
            FraudDetectionModel._models.clear()


def get_model() -> FraudDetectionModel:
    """The model configured for the current application"""
    from flask import current_app
    return FraudDetectionModel(current_app.config['MODEL_PATH'])
