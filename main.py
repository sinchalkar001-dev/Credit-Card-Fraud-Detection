"""Start the site for local use: python main.py

Trains the model first if there is no usable one (a few seconds, first run only).
For a production server, use wsgi.py instead.
"""

import os


def load_env_file(path):
    """Read KEY=VALUE lines from a .env file without overriding the real environment"""
    if not os.path.exists(path):
        return
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"\''))


# The configuration reads the environment when it is imported, so .env comes first.
load_env_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

from app import create_app  # noqa: E402
from train_model import ensure_model  # noqa: E402


def main():
    ensure_model()
    app = create_app()

    # Listens on this machine only unless HOST says otherwise.
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', os.environ.get('DEBUG', 'False')).lower() in ('1', 'true')

    print(f'Open http://{"localhost" if host in ("127.0.0.1", "0.0.0.0") else host}:{port} in your browser.')
    app.run(
        host=host,
        port=port,
        debug=debug
    )


if __name__ == '__main__':
    main()
