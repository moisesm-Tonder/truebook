"""
Seed script — creates default admin user.
Run once after migrations: python seed.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

DEFAULT_EMAIL = "admin@tonder.io"
DEFAULT_PASSWORD = "Tonder2026!"
DEFAULT_NAME = "Administrador"

db = SessionLocal()
try:
    existing = db.query(User).filter(User.email == DEFAULT_EMAIL).first()
    if existing:
        print(f"Usuario {DEFAULT_EMAIL} ya existe.")
    else:
        user = User(
            email=DEFAULT_EMAIL,
            full_name=DEFAULT_NAME,
            hashed_password=get_password_hash(DEFAULT_PASSWORD),
            role="admin",
        )
        db.add(user)
        db.commit()
        print(f"Usuario creado: {DEFAULT_EMAIL} / {DEFAULT_PASSWORD}")
finally:
    db.close()
