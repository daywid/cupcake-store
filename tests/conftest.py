import pytest

from app import create_app
from app.cli import popular
from app.extensions import db
from config import TestConfig


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        popular()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, senha):
    return client.post("/login", data={"email": email, "senha": senha}, follow_redirects=True)


@pytest.fixture
def cliente(client):
    login(client, "cliente@cupcake.com", "cliente12345")
    return client


@pytest.fixture
def admin(client):
    login(client, "admin@cupcake.com", "admin12345")
    return client
