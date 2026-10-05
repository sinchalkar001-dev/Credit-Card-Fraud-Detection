"""Figures shown on the Analytics and Performance pages.

Both are read from files on disk: the labelled dataset the model learns from,
and the scores train_model.py recorded. Results are cached until the file
changes.
"""

import json
import logging
import math
import os
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from app.utils.schema import FEATURES, FEATURES_BY_NAME, TARGET_CODES, TARGET_COLUMN

logger = logging.getLogger(__name__)

_cache: Dict[tuple, tuple] = {}

# (upper bound inclusive, label) per numeric feature; None closes the last band.
BANDS = {
    'credit_usage': ((12, 'Up to 12 months'), (24, '13 to 24 months'), (36, '25 to 36 months'),
                     (48, '37 to 48 months'), (None, 'Over 48 months')),
    'current_balance': ((999, 'Under 1,000'), (1999, '1,000 to 1,999'), (3999, '2,000 to 3,999'),
                        (7999, '4,000 to 7,999'), (None, '8,000 or more')),
    'cc_age': ((24, 'Under 25'), (34, '25 to 34'), (44, '35 to 44'), (54, '45 to 54'),
               (None, '55 or over')),
}

# Choice features whose options have a natural order. Their groups are listed
# in that order; every other breakdown is sorted by bad rate.
ORDERED = ('over_draft', 'average_credit_balance', 'employment', 'location',
           'residence_since', 'existing_credits', 'num_dependents')


def _cached(path: str, loader: Callable[[str], Any]) -> Optional[Any]:
    try:
        modified = os.path.getmtime(path)
    except OSError:
        return None

    key = (os.path.abspath(path), loader.__name__)
    hit = _cache.get(key)
    if hit and hit[0] == modified:
        return hit[1]

    try:
        value = loader(path)
    except Exception as e:
        logger.error(f"Could not read {path}: {str(e)}")
        return None

    _cache[key] = (modified, value)
    return value


def load_model_info(path: str) -> Optional[Dict[str, Any]]:
    """Scores recorded when the model was trained, or None if it has not been."""
    return _cached(path, _read_model_info)


def dataset_summary(path: str) -> Optional[Dict[str, Any]]:
    """Class balance of the labelled dataset and the bad rate along every model input."""
    return _cached(path, _summarise_dataset)


def _read_model_info(path: str) -> Dict[str, Any]:
    with open(path, encoding='utf-8') as f:
        info = json.load(f)

    for item in info.get('feature_importances', []):
        feature = FEATURES_BY_NAME.get(item['feature'])
        item['label'] = feature.label if feature else item['feature']
    return info


def _breakdown(label: str, bad: pd.Series, mask: pd.Series) -> Optional[Dict[str, Any]]:
    total = int(mask.sum())
    if total == 0:
        return None
    count = int(bad[mask].sum())
    return {'label': label, 'total': total, 'bad': count, 'rate': count / total}


def _summarise_dataset(path: str) -> Dict[str, Any]:
    df = pd.read_csv(path, encoding='unicode_escape')
    columns = {str(column).strip().lower(): column for column in df.columns}

    outcome = df[columns[TARGET_COLUMN]].astype(str).str.strip().str.lower().map(TARGET_CODES)
    df = df[outcome.notna()]
    bad = outcome[outcome.notna()].astype(int)

    dimensions: List[Dict[str, Any]] = []
    for feature in FEATURES:
        column = df[columns[feature.name]]
        rows = []

        if feature.kind == 'choice':
            wording = column.astype(str).str.strip().str.lower()
            for choice in feature.choices:
                rows.append(_breakdown(choice.label, bad, wording == choice.raw.lower()))
        else:
            values = pd.to_numeric(column, errors='coerce')
            lower = float('-inf')
            for upper, label in BANDS[feature.name]:
                ceiling = float('inf') if upper is None else upper
                rows.append(_breakdown(label, bad, (values > lower) & (values <= ceiling)))
                lower = ceiling

        rows = [row for row in rows if row]
        ordered = feature.kind == 'number' or feature.name in ORDERED
        if not ordered:
            rows.sort(key=lambda row: row['rate'], reverse=True)

        dimensions.append({
            'name': feature.name,
            'label': feature.label,
            'ordered': ordered,
            'rows': rows,
        })

    total = int(len(bad))
    count = int(bad.sum())
    highest = max((row['rate'] for dimension in dimensions for row in dimension['rows']), default=0.0)
    return {
        'rows': total,
        'bad': count,
        'good': total - count,
        'bad_rate': count / total if total else 0.0,
        # One scale for every breakdown, so bars stay comparable when the grouping changes.
        'rate_domain': max(0.1, math.ceil(highest * 10 - 1e-9) / 10),
        'dimensions': dimensions,
    }
