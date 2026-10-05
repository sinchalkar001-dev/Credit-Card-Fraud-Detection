"""Test suite. Run it from the project folder:

    python -m unittest discover -s tests -t .

The model file is a build product and is not kept in git, so the first run
trains it (a few seconds).
"""

from train_model import ensure_model

ensure_model(quiet=True)
