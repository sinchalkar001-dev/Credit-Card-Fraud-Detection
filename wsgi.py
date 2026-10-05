"""Entry point for a production WSGI server:

    gunicorn --bind 0.0.0.0:5000 wsgi:app

The Docker image trains the model while it is built, so this only trains when
it is run somewhere that has not.
"""

from app import create_app
from train_model import ensure_model

ensure_model(quiet=True)
app = create_app()
