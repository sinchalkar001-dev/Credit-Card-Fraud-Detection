import hmac
import secrets

from flask import abort, current_app, request, session

CSRF_SESSION_KEY = '_csrf_token'
CSRF_FIELD = 'csrf_token'
CSRF_HEADER = 'X-CSRF-Token'
SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS', 'TRACE')

CONTENT_SECURITY_POLICY = '; '.join((
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
))


def csrf_token() -> str:
    """Token tied to this browser session, created on first use"""
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def protect_from_csrf():
    """Reject form posts that do not carry this session's token"""
    if not current_app.config.get('CSRF_ENABLED', True):
        return
    if request.method in SAFE_METHODS or request.blueprint == 'api':
        return

    expected = session.get(CSRF_SESSION_KEY, '')
    sent = request.form.get(CSRF_FIELD) or request.headers.get(CSRF_HEADER, '')
    if not expected or not hmac.compare_digest(expected, sent):
        abort(400, description='This form expired. Reload the page and send it again.')


def add_security_headers(response):
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'DENY')
    response.headers.setdefault('Referrer-Policy', 'same-origin')
    response.headers.setdefault('Content-Security-Policy', CONTENT_SECURITY_POLICY)
    return response


def is_safe_redirect(target: str) -> bool:
    """Only follow redirects to a path on this site"""
    return bool(target) and target.startswith('/') and not target.startswith(('//', '/\\'))


def credentials_match(username: str, password: str) -> bool:
    expected_user = current_app.config['ADMIN_USERNAME']
    expected_password = current_app.config['ADMIN_PASSWORD']
    user_ok = hmac.compare_digest(username.encode(), expected_user.encode())
    password_ok = hmac.compare_digest(password.encode(), expected_password.encode())
    return user_ok and password_ok
