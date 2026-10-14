"""Atalho para popular o banco: `python database/seed.py` (equivale a `flask --app wsgi seed`)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.cli import popular  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Categoria  # noqa: E402
from wsgi import app  # noqa: E402

with app.app_context():
    db.create_all()
    if Categoria.query.first():
        print("O banco já tem dados. Use `flask --app wsgi init-db --reset` para recomeçar.")
    else:
        popular()
        print("Dados de demonstração inseridos.")
