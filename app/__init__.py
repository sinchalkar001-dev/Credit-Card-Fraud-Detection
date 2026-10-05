from flask import Flask, jsonify, render_template, request
import logging
import mimetypes
import os
import threading
from datetime import datetime
from werkzeug.exceptions import HTTPException
from app.config import config, DEFAULT_ADMIN_PASSWORD, DEFAULT_SECRET_KEY

# Windows takes these from the registry, where .js is often mapped to
# text/plain. Browsers refuse to run a script served that way.
mimetypes.add_type('text/javascript', '.js')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('image/svg+xml', '.svg')
mimetypes.add_type('font/woff2', '.woff2')


def create_app(config_name=None):
    """Application factory function"""

    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config.get(config_name, config['default']))

    setup_logging(app)
    register_security(app)
    register_template_helpers(app)
    register_blueprints(app)
    register_error_handlers(app)
    warn_about_defaults(app)
    warm_up_model(app)

    return app


def setup_logging(app):
    """Configure application logging"""
    app.logger.setLevel(logging.INFO)
    if app.testing:
        return

    # A log file is a convenience: if the folder is not writable, the console log carries on.
    try:
        log_folder = app.config.get('LOG_FOLDER')
        os.makedirs(log_folder, exist_ok=True)
        handler = logging.FileHandler(os.path.join(log_folder, 'app.log'))
    except OSError as e:
        app.logger.warning(f'Not writing logs/app.log: {e}')
        return

    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)


def register_security(app):
    """Check form posts and add browser security headers"""
    from app.utils.security import add_security_headers, protect_from_csrf

    app.before_request(protect_from_csrf)
    app.after_request(add_security_headers)


def register_template_helpers(app):
    """Values every template can use"""
    from app.utils.security import csrf_token

    @app.context_processor
    def inject_helpers():
        return {
            'csrf_token': csrf_token,
            'current_year': datetime.now().year,
        }

    @app.template_filter('number')
    def format_number(value, decimals=0):
        return f'{value:,.{decimals}f}'

    @app.template_filter('percent')
    def format_percent(value, decimals=0):
        """Format a 0-1 share as a percentage"""
        return f'{value * 100:.{decimals}f}%'


def register_blueprints(app):
    """Register Flask blueprints"""
    from app.routes import pages, auth, prediction, upload, api

    app.register_blueprint(pages.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(prediction.bp)
    app.register_blueprint(upload.bp)
    app.register_blueprint(api.bp)


def register_error_handlers(app):
    """Register error handlers"""

    pages = {
        400: ('That request could not be read',
              'Reload the page and send the form again.'),
        403: ('You do not have access to this page',
              'Sign in with an account that does, or go back to the home page.'),
        404: ('This page does not exist',
              'The address may be mistyped, or the page may have moved.'),
        405: ('That action is not available here',
              'Go back and use the buttons on the page.'),
        413: ('That file is too large',
              'Files can be up to 16 MB. Split the file into smaller ones and upload each.'),
        500: ('Something went wrong on our side',
              'Nothing was saved. Try again, and check logs/app.log if it keeps happening.'),
    }

    def render_error(status, description=None):
        title, hint = pages.get(status, pages[500])
        if description:
            hint = description
        accept = request.accept_mimetypes
        if request.path.startswith('/api/') or accept['application/json'] > accept['text/html']:
            return jsonify({'error': title, 'detail': hint}), status
        return render_template('error.html', status=status, title=title, hint=hint), status

    # Covers 500 as well: Flask logs the traceback, then wraps an unhandled
    # exception in InternalServerError before looking for a handler.
    @app.errorhandler(HTTPException)
    def http_error(error):
        # Werkzeug's stock descriptions are written for developers; only pass on our own.
        stock = type(error).description
        description = error.description if error.description != stock else None
        return render_error(error.code or 500, description)


def warm_up_model(app):
    """Load the model in the background, so the first check is not the slow one"""
    if app.testing:
        return

    from app.models.fraud_model import FraudDetectionModel, ModelUnavailable

    def load():
        try:
            FraudDetectionModel(app.config['MODEL_PATH']).load_model()
        except ModelUnavailable as e:
            app.logger.warning(str(e))

    threading.Thread(target=load, name='model-warm-up', daemon=True).start()


def warn_about_defaults(app):
    """Say so in the log when a live app runs on the demo secrets"""
    if app.debug or app.testing:
        return
    if app.config['SECRET_KEY'] == DEFAULT_SECRET_KEY:
        app.logger.warning('SECRET_KEY is the built-in default. Set SECRET_KEY before going live.')
    if app.config['ADMIN_PASSWORD'] == DEFAULT_ADMIN_PASSWORD:
        app.logger.warning('ADMIN_PASSWORD is the demo password. Set ADMIN_PASSWORD before going live.')
