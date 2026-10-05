import io
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from app.utils.schema import FEATURES, FEATURE_NAMES, TARGET_CODES, TARGET_COLUMN, describe_features
from app.utils.validators import PredictionValidator, parse_value

logger = logging.getLogger(__name__)


@dataclass
class Batch:
    """Rows of an uploaded file, ready for the model."""
    matrix: np.ndarray               # one row per readable record, columns in model order
    positions: List[int]             # position in the file of each matrix row
    errors: Dict[int, str]           # position in the file -> why the row was set aside
    labels: Optional[List[Optional[int]]]  # known outcome per file row, if the file has one


class DataPreprocessor:
    """Handles data preprocessing and feature engineering"""

    @staticmethod
    def read_csv(file) -> pd.DataFrame:
        """
        Parse an uploaded CSV file

        Accepts the byte-order mark Excel adds and legacy Windows encodings.
        Only empty cells count as missing: the dataset writes "none" as a
        value, and pandas would otherwise read a capitalised "None" as blank.

        Args:
            file: File-like object opened in binary mode

        Returns:
            DataFrame of the file's rows
        """
        content = file.read()
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = content.decode('cp1252', errors='replace')
        return pd.read_csv(io.StringIO(text), keep_default_na=False, na_values=[''])

    def preprocess_prediction_input(self, features_dict: dict) -> np.ndarray:
        """
        Preprocess raw input features for prediction

        Args:
            features_dict: Dictionary of raw feature values

        Returns:
            Preprocessed feature array ready for model

        Raises:
            ValueError: If a value is missing or cannot be read
        """
        values, errors = PredictionValidator.parse_features(features_dict)
        if errors:
            raise ValueError(' '.join(errors.values()))
        return np.array([values], dtype=float)

    def prepare_batch(self, df: pd.DataFrame) -> Batch:
        """
        Encode every row of an uploaded file for batch predictions

        Rows with a value the model cannot use are set aside with the reason
        instead of failing the whole file.

        Args:
            df: Input DataFrame holding at least the model's feature columns

        Returns:
            Batch with the encoded matrix and the rows that were set aside
        """
        columns = {str(column).strip().lower(): column for column in df.columns}
        feature_columns = [df[columns[name]].tolist() for name in FEATURE_NAMES]

        rows: List[List[float]] = []
        positions: List[int] = []
        errors: Dict[int, str] = {}

        for position, cells in enumerate(zip(*feature_columns)):
            encoded = []
            for feature, cell in zip(FEATURES, cells):
                number, error = parse_value(feature, cell)
                if error:
                    errors[position] = error
                    break
                encoded.append(number)
            else:
                rows.append(encoded)
                positions.append(position)

        if errors:
            logger.warning(f"{len(errors)} of {len(df)} uploaded rows could not be read")

        matrix = np.array(rows, dtype=float).reshape(len(rows), len(FEATURES))
        labels = self._read_labels(df[columns[TARGET_COLUMN]]) if TARGET_COLUMN in columns else None
        return Batch(matrix=matrix, positions=positions, errors=errors, labels=labels)

    @staticmethod
    def _read_labels(column: pd.Series) -> List[Optional[int]]:
        labels: List[Optional[int]] = []
        for value in column.tolist():
            wording = str(value).strip().lower()
            if wording in TARGET_CODES:
                labels.append(TARGET_CODES[wording])
            elif wording in ('0', '0.0', '1', '1.0'):
                labels.append(int(float(wording)))
            else:
                labels.append(None)
        return labels

    @staticmethod
    def get_feature_description() -> dict:
        """Get description of all features"""
        return describe_features()
