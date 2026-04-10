import sys
import os

# Add Backend to Python path so app.* imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Backend'))

from app.main import app  # noqa: F401 — Vercel picks up `app` as the ASGI handler
