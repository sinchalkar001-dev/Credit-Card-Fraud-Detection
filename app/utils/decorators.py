from flask import session, redirect, request, url_for, flash
from functools import wraps
import logging

logger = logging.getLogger(__name__)


def _login_url():
    """Login page that returns to the page the visitor asked for"""
    if request.method == 'GET':
        return url_for('auth.login', next=request.full_path.rstrip('?'))
    return url_for('auth.login')


def login_required(f):
    """Decorator to require login for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Sign in to continue.', 'warning')
            return redirect(_login_url())
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Sign in to continue.', 'warning')
            return redirect(_login_url())
        if session.get('role') != 'admin':
            flash('That page needs an admin account.', 'danger')
            return redirect(url_for('pages.index'))
        return f(*args, **kwargs)
    return decorated_function
