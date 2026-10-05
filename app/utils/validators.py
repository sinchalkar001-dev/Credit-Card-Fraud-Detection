import logging
import math
from typing import Any, Dict, List, Mapping, Optional, Tuple

from app.utils.schema import FEATURES, FEATURE_NAMES, TARGET_COLUMN, Feature

logger = logging.getLogger(__name__)


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return isinstance(value, str) and not value.strip()


def _as_number(value: Any) -> Optional[float]:
    """Read a finite number, or None if the value is not one."""
    if isinstance(value, bool):
        return None
    try:
        number = float(value.strip() if isinstance(value, str) else value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _format_bound(bound: float) -> str:
    return f'{bound:,.0f}' if float(bound).is_integer() else f'{bound:,}'


def parse_value(feature: Feature, value: Any) -> Tuple[Optional[float], Optional[str]]:
    """Turn one submitted value into the number the model expects.

    Returns (number, None) on success or (None, message) when the value cannot
    be used. Choice fields accept the model code, the dataset wording or the
    label shown in the interface.
    """
    name = feature.label.lower()

    if feature.kind == 'number':
        if _is_blank(value):
            return None, f'Enter {name}.'
        number = _as_number(value)
        if number is None:
            return None, f'{feature.label} must be a number.'
        if feature.integer and not number.is_integer():
            return None, f'{feature.label} must be a whole number.'
        if not (feature.minimum <= number <= feature.maximum):
            unit = f' {feature.unit}' if feature.unit else ''
            return None, (
                f'{feature.label} must be between {_format_bound(feature.minimum)} '
                f'and {_format_bound(feature.maximum)}{unit}.'
            )
        return number, None

    if _is_blank(value):
        return None, f'Choose an option for {name}.'
    number = _as_number(value)
    if number is not None:
        if number.is_integer() and feature.choice_for(int(number)) is not None:
            return float(int(number)), None
    else:
        wording = str(value).strip().lower()
        for choice in feature.choices:
            if wording in (choice.raw.lower(), choice.label.lower()):
                return float(choice.code), None
    return None, f'Choose one of the listed options for {name}.'


class PredictionValidator:
    """Validates input data for predictions"""

    @staticmethod
    def parse_features(features: Mapping[str, Any]) -> Tuple[Optional[List[float]], Dict[str, str]]:
        """
        Read every model input from a submitted form or JSON body

        Args:
            features: Mapping of feature names to submitted values. Keys the
                model does not use are ignored.

        Returns:
            Tuple of (values in model order or None, error message per field)
        """
        values: List[float] = []
        errors: Dict[str, str] = {}

        for feature in FEATURES:
            number, error = parse_value(feature, features.get(feature.name))
            if error:
                errors[feature.name] = error
            else:
                values.append(number)

        if errors:
            return None, errors
        return values, {}

    @staticmethod
    def validate_features(features: Mapping[str, Any]) -> Tuple[bool, str]:
        """
        Validate prediction features

        Args:
            features: Dictionary of feature names and values

        Returns:
            Tuple of (is_valid, error_message)
        """
        _, errors = PredictionValidator.parse_features(features)
        if errors:
            first = next(name for name in FEATURE_NAMES if name in errors)
            return False, errors[first]
        return True, ''

    @staticmethod
    def validate_csv_structure(df) -> Tuple[bool, str]:
        """
        Validate CSV file structure

        Column names are matched without regard to case, so the dataset's own
        `Average_Credit_Balance` header is accepted. Columns the model does not
        use, including the optional `class` label, are allowed.

        Args:
            df: Pandas DataFrame

        Returns:
            Tuple of (is_valid, error_message)
        """
        if df.empty:
            return False, 'The file has no rows. Add at least one row under the header and upload it again.'

        present = {str(column).strip().lower() for column in df.columns}
        missing = [name for name in FEATURE_NAMES if name not in present]
        if missing:
            noun = 'this column' if len(missing) == 1 else 'these columns'
            return False, f"The file is missing {noun}: {', '.join(missing)}."

        return True, ''

    @staticmethod
    def has_labels(df) -> bool:
        """Whether the file carries the known outcome for each row."""
        return TARGET_COLUMN in {str(column).strip().lower() for column in df.columns}


class FileValidator:
    """Validates file uploads"""

    ALLOWED_EXTENSIONS = {'csv'}
    MAX_FILE_SIZE = 16 * 1024 * 1024  # 16 MB

    @staticmethod
    def allowed_file(filename: str) -> bool:
        """Check if file extension is allowed"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in FileValidator.ALLOWED_EXTENSIONS

    @staticmethod
    def validate_file(filename: str, file_size: int) -> Tuple[bool, str]:
        """
        Validate uploaded file

        Args:
            filename: Name of the file
            file_size: Size of the file in bytes

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not FileValidator.allowed_file(filename):
            return False, 'Only CSV files can be scored. Export the sheet as .csv and upload it again.'

        if file_size == 0:
            return False, 'The file is empty. Choose a CSV with a header row and at least one row of data.'

        if file_size > FileValidator.MAX_FILE_SIZE:
            limit = FileValidator.MAX_FILE_SIZE / (1024 * 1024)
            return False, f'The file is larger than {limit:.0f} MB. Split it into smaller files and upload each one.'

        return True, ''
