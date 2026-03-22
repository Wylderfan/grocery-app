"""Shared pytest fixtures for the grocery-app test suite.

Uses an in-memory SQLite database so tests are fast, self-contained,
and require no MySQL server.
"""

import os
import pytest

# Force the app into testing mode with an in-memory SQLite database BEFORE
# any application code is imported, so config picks up the env var.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("PROFILES", "TestUser")


from app import create_app, db as _db
from app.models import Grocery


@pytest.fixture(scope="session")
def app():
    """Create the Flask application configured for testing."""
    application = create_app("development")
    application.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        WTF_CSRF_ENABLED=False,
        SECRET_KEY="test-secret",
        PROFILES=["TestUser"],
    )

    with application.app_context():
        _db.create_all()
        yield application
        _db.drop_all()


@pytest.fixture(scope="function")
def db(app):
    """Provide a clean database for each test by rolling back after each test."""
    with app.app_context():
        yield _db
        _db.session.rollback()
        # Delete all rows between tests to keep state isolated.
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


@pytest.fixture(scope="function")
def client(app, db):
    """Flask test client with an active session profile."""
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess["profile"] = "TestUser"
        yield c


@pytest.fixture()
def grocery_factory(db, app):
    """Return a helper that creates and commits a Grocery row."""

    def make(name="Milk", status="Need", purchased_date=None, shelf_life_days=None, **kwargs):
        with app.app_context():
            g = Grocery(
                profile_id="TestUser",
                name=name,
                status=status,
                purchased_date=purchased_date,
                shelf_life_days=shelf_life_days,
                **kwargs,
            )
            db.session.add(g)
            db.session.commit()
            # Return the id so callers can re-fetch inside app context
            return g.id

    return make
