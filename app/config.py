import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

DEFAULT_SECRET_KEY = 'dev-secret-key-change-in-production'
DEFAULT_ADMIN_USERNAME = 'admin'
DEFAULT_ADMIN_PASSWORD = 'admin123'


class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or DEFAULT_SECRET_KEY
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False') == 'True'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    CSRF_ENABLED = True

    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or DEFAULT_ADMIN_USERNAME
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or DEFAULT_ADMIN_PASSWORD

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max file size
    MAX_BATCH_ROWS = 10000  # rows scored per uploaded file
    PREVIEW_ROWS = 1000  # rows listed on the results page, riskiest first
    LOG_FOLDER = os.path.join(BASE_DIR, 'logs')

    MODEL_PATH = os.path.join(BASE_DIR, 'model', 'credit.pkl')
    MODEL_INFO_PATH = os.path.join(BASE_DIR, 'model', 'model_info.json')
    DATASET_PATH = os.path.join(BASE_DIR, 'data', 'credit_data.csv')
    SAMPLE_CSV_PATH = os.path.join(BASE_DIR, 'data', 'sample_upload.csv')

    ALLOWED_EXTENSIONS = {'csv'}

    DEBUG = False
    TESTING = False


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    # Browsers only keep a secure cookie over HTTPS (or on localhost). Set
    # SESSION_COOKIE_SECURE=False to sign in over plain HTTP on a private network.
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'True') == 'True'


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
