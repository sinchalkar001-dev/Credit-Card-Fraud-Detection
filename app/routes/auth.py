from flask import Blueprint, current_app, render_template, request, session, redirect, url_for, flash
import logging
from app.config import DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME
from app.utils.security import credentials_match, is_safe_redirect

logger = logging.getLogger(__name__)

bp = Blueprint('auth', __name__, url_prefix='/')


def _demo_credentials():
    """The built-in login, shown on the sign-in page until it has been replaced"""
    if (current_app.config['ADMIN_USERNAME'] == DEFAULT_ADMIN_USERNAME
            and current_app.config['ADMIN_PASSWORD'] == DEFAULT_ADMIN_PASSWORD):
        return {'username': DEFAULT_ADMIN_USERNAME, 'password': DEFAULT_ADMIN_PASSWORD}
    return None


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication"""
    next_url = request.values.get('next', '')
    if not is_safe_redirect(next_url):
        next_url = ''

    if request.method == 'GET' and 'user_id' in session:
        return redirect(next_url or url_for('pages.index'))

    error = None
    username = ''

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            error = 'Enter both your username and your password.'
            logger.warning(f"Login attempt with missing credentials from {request.remote_addr}")
        elif credentials_match(username, password):
            session.clear()
            session.permanent = True
            session['user_id'] = username
            session['role'] = 'admin'
            logger.info(f"User {username} logged in successfully")
            flash(f'Signed in as {username}.', 'success')
            return redirect(next_url or url_for('pages.index'))
        else:
            error = 'That username and password do not match. Check both and try again.'
            logger.warning(f"Failed login attempt for user {username} from {request.remote_addr}")

    return render_template(
        'login.html',
        error=error,
        username=username,
        next_url=next_url,
        demo=_demo_credentials(),
    ), (401 if error else 200)


@bp.route('/logout', methods=['GET', 'POST'])
def logout():
    """Logout user"""
    username = session.get('user_id', 'Unknown')
    session.clear()
    logger.info(f"User {username} logged out")
    flash('Signed out.', 'info')
    return redirect(url_for('auth.login'))
