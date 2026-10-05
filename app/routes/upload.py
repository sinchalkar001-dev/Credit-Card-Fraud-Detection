from flask import Blueprint, abort, current_app, render_template, request, redirect, url_for, send_file
import logging
import os
import pandas as pd
from werkzeug.utils import secure_filename
from app.utils.decorators import login_required
from app.utils.validators import FileValidator, PredictionValidator
from app.utils.preprocessing import DataPreprocessor
from app.utils.schema import FEATURES, FEATURES_BY_NAME, TARGET_COLUMN
from app.models.fraud_model import ModelUnavailable, get_model

logger = logging.getLogger(__name__)

bp = Blueprint('upload', __name__, url_prefix='/')
preprocessor = DataPreprocessor()

# Columns echoed next to each prediction so a row can be recognised.
SHOWN_COLUMNS = ('current_balance', 'credit_usage', 'cc_age', 'purpose')


def _render_upload(error=None, status=200):
    return render_template(
        'upload.html',
        error=error,
        features=FEATURES,
        label_column=TARGET_COLUMN,
        max_rows=current_app.config['MAX_BATCH_ROWS'],
        max_megabytes=current_app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024),
        has_sample=os.path.exists(current_app.config['SAMPLE_CSV_PATH']),
    ), status


def _file_size(file):
    stream = file.stream
    position = stream.tell()
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(position)
    return size


def _score(df, batch):
    """Join every uploaded row with its prediction, in file order"""
    predictions = dict(zip(batch.positions, get_model().predict_many(batch.matrix)))
    columns = {str(column).strip().lower(): column for column in df.columns}
    # Empty cells arrive as NaN; show them as blanks.
    shown = [df[columns[name]].astype(object).where(df[columns[name]].notna(), '').tolist()
             for name in SHOWN_COLUMNS]

    rows = []
    for position in range(len(df)):
        prediction = predictions.get(position)
        actual = batch.labels[position] if batch.labels else None
        row = {
            'number': position + 1,
            'cells': [values[position] for values in shown],
            'error': batch.errors.get(position),
            'actual': actual,
        }
        if prediction:
            flagged = prediction['flagged']
            row.update(
                flagged=flagged,
                risk_score=prediction['risk_score'],
                matches=None if actual is None else (actual == 1) == flagged,
            )
        rows.append(row)
    return rows


def _summarise(rows):
    scored = [row for row in rows if not row['error']]
    flagged = sum(1 for row in scored if row['flagged'])
    labelled = [row for row in scored if row['matches'] is not None]

    summary = {
        'total': len(rows),
        'scored': len(scored),
        'skipped': len(rows) - len(scored),
        'flagged': flagged,
        'cleared': len(scored) - flagged,
        'flagged_share': flagged / len(scored) if scored else 0.0,
        'labelled': len(labelled),
    }
    if labelled:
        summary['matched'] = sum(1 for row in labelled if row['matches'])
        summary['agreement'] = summary['matched'] / len(labelled)
    return summary


@bp.route('/upload', methods=['GET'])
@login_required
def upload():
    """File upload page"""
    return _render_upload()


@bp.route('/upload/sample', methods=['GET'])
@login_required
def sample():
    """A small CSV in the expected layout"""
    path = current_app.config['SAMPLE_CSV_PATH']
    if not os.path.exists(path):
        abort(404)
    return send_file(path, mimetype='text/csv', as_attachment=True,
                     download_name='sample-applications.csv')


@bp.route('/preview', methods=['GET'])
@login_required
def preview_redirect():
    """Results only exist right after an upload"""
    return redirect(url_for('upload.upload'))


@bp.route('/preview', methods=['POST'])
@login_required
def preview():
    """Score an uploaded CSV file and show the results"""
    file = request.files.get('datasetfile')
    if file is None or file.filename == '':
        return _render_upload('Choose a CSV file to score.', 400)

    is_valid, error_msg = FileValidator.validate_file(file.filename, _file_size(file))
    if not is_valid:
        return _render_upload(error_msg, 400)

    try:
        df = preprocessor.read_csv(file)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as e:
        logger.error(f"CSV parsing error: {str(e)}")
        return _render_upload(
            'The file could not be read as CSV. Check that it has a header row and '
            'comma-separated values, then upload it again.', 400)

    is_valid_csv, csv_error = PredictionValidator.validate_csv_structure(df)
    if not is_valid_csv:
        return _render_upload(csv_error, 400)

    max_rows = current_app.config['MAX_BATCH_ROWS']
    if len(df) > max_rows:
        return _render_upload(
            f'The file has {len(df):,} rows. Up to {max_rows:,} can be scored at once, '
            'so split it into smaller files.', 400)

    try:
        rows = _score(df, preprocessor.prepare_batch(df))
    except ModelUnavailable as e:
        logger.error(f"Batch scoring unavailable: {str(e)}")
        return _render_upload(str(e), 503)

    summary = _summarise(rows)
    # Lead with the rows that need attention: riskiest first, unreadable rows last.
    rows.sort(key=lambda row: (row['error'] is not None, -row.get('risk_score', 0.0)))

    logger.info(f"File {file.filename} scored: {summary['flagged']} of {summary['scored']} rows flagged")
    return render_template(
        'results.html',
        filename=secure_filename(file.filename),
        summary=summary,
        rows=rows[:current_app.config['PREVIEW_ROWS']],
        shown_columns=[FEATURES_BY_NAME[name].label for name in SHOWN_COLUMNS],
        total_rows=len(df))

