from flask import Blueprint, current_app, render_template
import logging
from app.utils.decorators import login_required
from app.utils.insights import dataset_summary, load_model_info

logger = logging.getLogger(__name__)

bp = Blueprint('pages', __name__, url_prefix='/')


# Decorators apply bottom-up: '/' registers first, so url_for builds it.
@bp.route('/index', methods=['GET'])
@bp.route('/', methods=['GET'])
def index():
    """Home page"""
    return render_template(
        'index.html',
        summary=dataset_summary(current_app.config['DATASET_PATH']),
        model_info=load_model_info(current_app.config['MODEL_INFO_PATH']))


@bp.route('/chart', methods=['GET'])
@login_required
def analytics():
    """Dataset analytics: class balance and bad rates by every input"""
    return render_template(
        'analytics.html',
        summary=dataset_summary(current_app.config['DATASET_PATH']))


@bp.route('/performance', methods=['GET'])
@login_required
def performance():
    """Model performance on the held-out applications"""
    return render_template(
        'performance.html',
        model_info=load_model_info(current_app.config['MODEL_INFO_PATH']))
