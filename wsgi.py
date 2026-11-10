"""
Production entry point (gunicorn):  gunicorn wsgi:app
Seeds demo data only when the connected database has no users, so judges always have
working demo accounts and nothing is ever wiped.
"""
import logging
import os

from app import create_app
from app.repositories.user_repository import UserRepository

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
app = create_app()

if os.getenv("AUTO_SEED_DEMO_DATA", "1").lower() in ("1", "true", "yes"):
    with app.app_context():
        try:
            if UserRepository.count() == 0:
                from scripts.seed_database import seed
                logging.getLogger(__name__).info("Empty database: seeding demo accounts and reports")
                seed(app=app, force=True)
        except Exception as exc:  # never block startup on seeding
            logging.getLogger(__name__).error("Demo seed skipped: %s", exc)
