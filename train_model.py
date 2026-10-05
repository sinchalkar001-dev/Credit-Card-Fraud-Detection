"""Train the credit-risk model and record how it performs.

    python train_model.py

Reads data/credit_data.csv (1,000 labelled applications, 20 attributes, 30%
marked bad) and writes two files the app loads:

    model/credit.pkl        the fitted classifier
    model/model_info.json   every score shown on the Performance page

How the model is tested, so that the scores mean what they say:

1. 20% of the applications are set aside first, keeping the 70/30 class mix
   (a stratified split). Nothing below looks at them until the final scoring.
2. Tree depth, tree count and learning rate are chosen by 5-fold
   cross-validation on the other 80%, by ROC AUC.
3. The classes are uneven, so each bad application is weighted to count as
   much as 2.33 good ones. The same settings are also fitted without weights
   and both versions are scored, to show what the weighting buys and costs.
4. The weighted model, fitted on the 80%, is the one saved and served. Its
   scores come from the 200 applications it has never seen.

Nothing is oversampled, so a held-out application can never be a copy of a
training one.

A pickled classifier only loads in the scikit-learn version that wrote it,
so run this again after upgrading scikit-learn.
"""

import json
import os
import pickle
import platform
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.utils.class_weight import compute_sample_weight

from app.utils.preprocessing import DataPreprocessor
from app.utils.schema import FEATURE_NAMES

ROOT = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(ROOT, 'data', 'credit_data.csv')
MODEL_PATH = os.path.join(ROOT, 'model', 'credit.pkl')
MODEL_INFO_PATH = os.path.join(ROOT, 'model', 'model_info.json')

SEED = 42
TEST_SIZE = 0.2
FOLDS = 5
SUBSAMPLE = 0.8

# Shallow trees with a small step: the dataset is too small for anything deeper
# to generalise. Tree count and learning rate are searched as pairs.
SEARCH_SPACE = [
    {'max_depth': [1, 2, 3], 'n_estimators': [150], 'learning_rate': [0.1]},
    {'max_depth': [1, 2, 3], 'n_estimators': [300], 'learning_rate': [0.05]},
]

METRICS = ('accuracy', 'precision', 'recall', 'f1', 'roc_auc')


def load_dataset(path=DATASET_PATH):
    """Read the dataset and encode it with the app's own feature schema."""
    df = pd.read_csv(path, encoding='unicode_escape')
    batch = DataPreprocessor().prepare_batch(df)
    if batch.errors:
        position, reason = next(iter(batch.errors.items()))
        raise SystemExit(f'Row {position + 2} of {path} could not be read: {reason}')
    return batch.matrix, np.array(batch.labels, dtype=int)


def new_model(params):
    return GradientBoostingClassifier(subsample=SUBSAMPLE, random_state=SEED, **params)


def weights_for(y, weighted):
    return compute_sample_weight('balanced', y) if weighted else None


def score(model, X, y):
    """Scores for the bad class at the 50% line, plus the threshold-free ROC AUC."""
    risk = model.predict_proba(X)[:, list(model.classes_).index(1)]
    flagged = (risk > 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, flagged, labels=[0, 1]).ravel()
    return {
        'accuracy': float(accuracy_score(y, flagged)),
        'precision': float(precision_score(y, flagged, zero_division=0)),
        'recall': float(recall_score(y, flagged, zero_division=0)),
        'f1': float(f1_score(y, flagged, zero_division=0)),
        'roc_auc': float(roc_auc_score(y, risk)),
        'confusion_matrix': {'tn': int(tn), 'fp': int(fp), 'fn': int(fn), 'tp': int(tp)},
    }


def choose_params(X_train, y_train):
    """Pick depth, tree count and learning rate by cross-validated ROC AUC."""
    folds = StratifiedKFold(n_splits=FOLDS, shuffle=True, random_state=SEED)
    search = GridSearchCV(
        GradientBoostingClassifier(subsample=SUBSAMPLE, random_state=SEED),
        SEARCH_SPACE, scoring='roc_auc', cv=folds, refit=False)
    search.fit(X_train, y_train, sample_weight=weights_for(y_train, weighted=True))

    results = search.cv_results_
    candidates = sorted(
        ({'params': params, 'roc_auc': float(mean), 'roc_auc_std': float(std)}
         for params, mean, std in zip(results['params'], results['mean_test_score'], results['std_test_score'])),
        key=lambda candidate: candidate['roc_auc'], reverse=True)
    return dict(search.best_params_), candidates


def cross_validate(params, X_train, y_train, weighted):
    """Mean and spread of every score across the folds of the training rows."""
    folds = StratifiedKFold(n_splits=FOLDS, shuffle=True, random_state=SEED)
    per_fold = []
    for fit_rows, check_rows in folds.split(X_train, y_train):
        model = new_model(params)
        model.fit(X_train[fit_rows], y_train[fit_rows],
                  sample_weight=weights_for(y_train[fit_rows], weighted))
        per_fold.append(score(model, X_train[check_rows], y_train[check_rows]))

    return {
        metric: {
            'mean': float(np.mean([fold[metric] for fold in per_fold])),
            'std': float(np.std([fold[metric] for fold in per_fold])),
        }
        for metric in METRICS
    }


def evaluate(params, X_train, y_train, X_test, y_test, weighted):
    model = new_model(params)
    model.fit(X_train, y_train, sample_weight=weights_for(y_train, weighted))
    return model, {
        'test': score(model, X_test, y_test),
        'cross_validation': cross_validate(params, X_train, y_train, weighted),
    }


def train(quiet=False):
    """Fit, score and save the model. Returns what was written to model_info.json."""
    say = (lambda *args: None) if quiet else print
    started = time.time()

    X, y = load_dataset()
    say(f'Dataset: {len(y)} applications, {int(y.sum())} bad, {int((y == 0).sum())} good')

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=SEED)

    params, candidates = choose_params(X_train, y_train)
    say(f'Chosen by {FOLDS}-fold cross-validation: {params}')

    model, weighted = evaluate(params, X_train, y_train, X_test, y_test, weighted=True)
    _, unweighted = evaluate(params, X_train, y_train, X_test, y_test, weighted=False)

    baseline = float(max(np.mean(y_test), 1 - np.mean(y_test)))
    for name, evaluation in (('Weighted (saved)', weighted), ('Unweighted', unweighted)):
        test = evaluation['test']
        say(f"{name:<17} ROC AUC {test['roc_auc']:.3f}  accuracy {test['accuracy']:.3f}  "
            f"precision {test['precision']:.3f}  recall {test['recall']:.3f}  F1 {test['f1']:.3f}")
    say(f'Always answering "good" would score {baseline:.3f} accuracy on the same test rows')

    importances = sorted(
        ({'feature': name, 'importance': float(weight)}
         for name, weight in zip(FEATURE_NAMES, model.feature_importances_)),
        key=lambda item: item['importance'], reverse=True)

    info = {
        'algorithm': 'Gradient Boosting',
        'estimator': type(model).__name__,
        'params': dict(params, subsample=SUBSAMPLE, random_state=SEED),
        'class_weighting': 'balanced',
        'trained_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'library_versions': {
            'python': platform.python_version(),
            'scikit-learn': sklearn.__version__,
            'numpy': np.__version__,
            'pandas': pd.__version__,
        },
        'features': list(FEATURE_NAMES),
        'dataset': {
            'rows': int(len(y)),
            'bad': int(y.sum()),
            'good': int((y == 0).sum()),
        },
        'split': {
            'train_rows': int(len(y_train)),
            'test_rows': int(len(y_test)),
            'test_size': TEST_SIZE,
            'stratified': True,
            'random_state': SEED,
        },
        'baseline_accuracy': baseline,
        'tuning': {'metric': 'roc_auc', 'folds': FOLDS, 'candidates': candidates},
        'evaluations': {'weighted': weighted, 'unweighted': unweighted},
        'serving': 'weighted',
        'feature_importances': importances,
    }

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
    with open(MODEL_INFO_PATH, 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=2)
        f.write('\n')

    say(f'Wrote {os.path.relpath(MODEL_PATH, ROOT)} and {os.path.relpath(MODEL_INFO_PATH, ROOT)} '
        f'in {time.time() - started:.0f}s')
    return info


def artifacts_ready():
    """True when a model this code can use is already on disk."""
    if not (os.path.exists(MODEL_PATH) and os.path.exists(MODEL_INFO_PATH)):
        return False
    try:
        with open(MODEL_PATH, 'rb') as f:
            model = pickle.load(f)
        with open(MODEL_INFO_PATH, encoding='utf-8') as f:
            info = json.load(f)
    except Exception:
        return False
    return (getattr(model, 'n_features_in_', None) == len(FEATURE_NAMES)
            and info.get('features') == list(FEATURE_NAMES)
            and 'evaluations' in info)


def ensure_model(quiet=False):
    """Train on first run, or when the saved model no longer fits the code."""
    if artifacts_ready():
        return
    if not quiet:
        print('No usable model found. Training one now; this takes a few seconds.')
    train(quiet=quiet)


if __name__ == '__main__':
    train()
