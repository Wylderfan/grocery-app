"""Tests for issue #2 — expiry notifications.

Covers:
  - days_until_expiry computed property edge cases
  - got_it route: sets purchased_date when None, does not overwrite existing date
  - bulk_have route: sets purchased_date on None rows only
  - add route: persists shelf_life_days
  - edit route: updates shelf_life_days
"""

from datetime import date, timedelta

import pytest

from app.models import Grocery
from app import db as _db


# ---------------------------------------------------------------------------
# days_until_expiry property
# ---------------------------------------------------------------------------

class TestDaysUntilExpiry:
    """Unit tests for the Grocery.days_until_expiry computed property.

    SQLAlchemy mapped columns need a proper app context and session to be set,
    so we create transient (not yet persisted) Grocery objects inside the app
    context using the normal constructor — no DB flush required.
    """

    def _grocery(self, app, purchased_date=None, shelf_life_days=None):
        """Create an unsaved Grocery inside the app context."""
        with app.app_context():
            g = Grocery(
                profile_id="TestUser",
                name="_test_expiry_prop_",
                purchased_date=purchased_date,
                shelf_life_days=shelf_life_days,
            )
            return g.days_until_expiry  # read the property before leaving context

    def test_returns_none_when_purchased_date_is_none(self, app):
        result = self._grocery(app, purchased_date=None, shelf_life_days=7)
        assert result is None

    def test_returns_none_when_shelf_life_days_is_none(self, app):
        result = self._grocery(app, purchased_date=date.today(), shelf_life_days=None)
        assert result is None

    def test_returns_none_when_both_fields_are_none(self, app):
        result = self._grocery(app, purchased_date=None, shelf_life_days=None)
        assert result is None

    def test_returns_positive_int_when_not_expired(self, app):
        purchased = date.today() - timedelta(days=2)
        result = self._grocery(app, purchased_date=purchased, shelf_life_days=10)
        assert isinstance(result, int)
        assert result > 0  # 8 days left

    def test_returns_zero_on_expiry_day(self, app):
        # Purchased shelf_life_days ago — expires today.
        purchased = date.today() - timedelta(days=5)
        result = self._grocery(app, purchased_date=purchased, shelf_life_days=5)
        assert result == 0

    def test_returns_negative_int_when_expired(self, app):
        # Purchased 10 days ago with a 3-day shelf life — 7 days past expiry.
        purchased = date.today() - timedelta(days=10)
        result = self._grocery(app, purchased_date=purchased, shelf_life_days=3)
        assert isinstance(result, int)
        assert result < 0

    def test_exact_days_remaining_calculation(self, app):
        # Purchased today with 7-day shelf life → 7 days remaining.
        result = self._grocery(app, purchased_date=date.today(), shelf_life_days=7)
        assert result == 7

    def test_one_day_shelf_life_purchased_today(self, app):
        result = self._grocery(app, purchased_date=date.today(), shelf_life_days=1)
        assert result == 1


# ---------------------------------------------------------------------------
# got_it route
# ---------------------------------------------------------------------------

class TestGotItRoute:

    def test_sets_purchased_date_when_none(self, client, app, grocery_factory):
        """got_it should set purchased_date to today if it was previously None."""
        item_id = grocery_factory(name="Eggs", status="Need", purchased_date=None)

        response = client.post(
            f"/groceries/{item_id}/got-it",
            follow_redirects=True,
        )
        assert response.status_code == 200

        with app.app_context():
            item = _db.session.get(Grocery, item_id)
            assert item.purchased_date == date.today()
            assert item.status == "Have"

    def test_does_not_overwrite_existing_purchased_date(self, client, app, grocery_factory):
        """got_it must NOT change purchased_date if it is already set."""
        original_date = date.today() - timedelta(days=3)
        item_id = grocery_factory(
            name="Butter",
            status="Need",
            purchased_date=original_date,
        )

        client.post(f"/groceries/{item_id}/got-it", follow_redirects=True)

        with app.app_context():
            item = _db.session.get(Grocery, item_id)
            assert item.purchased_date == original_date  # unchanged
            assert item.status == "Have"

    def test_got_it_returns_redirect(self, client, grocery_factory):
        """got_it route must redirect (302) or follow to 200 on success."""
        item_id = grocery_factory(name="Cheese")
        response = client.post(f"/groceries/{item_id}/got-it")
        # Without follow_redirects the response should be a redirect.
        assert response.status_code in (301, 302, 200)


# ---------------------------------------------------------------------------
# bulk_have route
# ---------------------------------------------------------------------------

class TestBulkHaveRoute:

    def test_sets_purchased_date_on_items_with_none(self, client, app, grocery_factory):
        """bulk_have should set purchased_date = today for items that had None."""
        id1 = grocery_factory(name="Apple",  status="Need", purchased_date=None)
        id2 = grocery_factory(name="Banana", status="Need", purchased_date=None)

        response = client.post(
            "/groceries/bulk-have",
            data={"item_ids": [str(id1), str(id2)]},
            follow_redirects=True,
        )
        assert response.status_code == 200

        with app.app_context():
            for item_id in (id1, id2):
                item = _db.session.get(Grocery, item_id)
                assert item.purchased_date == date.today()
                assert item.status == "Have"

    def test_does_not_overwrite_existing_purchased_date_in_bulk(
        self, client, app, grocery_factory
    ):
        """bulk_have must NOT overwrite purchased_date if it was already set."""
        original = date.today() - timedelta(days=5)
        item_id = grocery_factory(
            name="Yogurt",
            status="Need",
            purchased_date=original,
        )

        client.post(
            "/groceries/bulk-have",
            data={"item_ids": [str(item_id)]},
            follow_redirects=True,
        )

        with app.app_context():
            item = _db.session.get(Grocery, item_id)
            assert item.purchased_date == original  # unchanged

    def test_bulk_have_mixed_items(self, client, app, grocery_factory):
        """bulk_have sets date only on the None items; the existing date is preserved."""
        old_date = date.today() - timedelta(days=2)
        id_with_date = grocery_factory(name="OldItem",  status="Need", purchased_date=old_date)
        id_without   = grocery_factory(name="NewItem",  status="Need", purchased_date=None)

        client.post(
            "/groceries/bulk-have",
            data={"item_ids": [str(id_with_date), str(id_without)]},
            follow_redirects=True,
        )

        with app.app_context():
            item_old = _db.session.get(Grocery, id_with_date)
            item_new = _db.session.get(Grocery, id_without)
            assert item_old.purchased_date == old_date
            assert item_new.purchased_date == date.today()

    def test_bulk_have_empty_selection_does_not_crash(self, client):
        """bulk_have with no item_ids selected should not error."""
        response = client.post(
            "/groceries/bulk-have",
            data={},
            follow_redirects=True,
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# add route — shelf_life_days persistence
# ---------------------------------------------------------------------------

class TestAddRoute:

    def test_add_saves_shelf_life_days(self, client, app):
        """POST /groceries/add should persist shelf_life_days when provided."""
        response = client.post(
            "/groceries/add",
            data={
                "name": "Whole Milk",
                "quantity": "1",
                "unit": "gallon",
                "category": "Dairy",
                "status": "Need",
                "shelf_life_days": "7",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        with app.app_context():
            item = Grocery.query.filter_by(profile_id="TestUser", name="Whole Milk").first()
            assert item is not None
            assert item.shelf_life_days == 7

    def test_add_shelf_life_days_none_when_omitted(self, client, app):
        """POST /groceries/add with no shelf_life_days should store None."""
        response = client.post(
            "/groceries/add",
            data={
                "name": "Plain Crackers",
                "status": "Need",
                # shelf_life_days intentionally omitted
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        with app.app_context():
            item = Grocery.query.filter_by(profile_id="TestUser", name="Plain Crackers").first()
            assert item is not None
            assert item.shelf_life_days is None

    def test_add_upsert_updates_shelf_life_days(self, client, app, grocery_factory):
        """Re-adding an existing item (upsert) should update shelf_life_days."""
        grocery_factory(name="Orange Juice", shelf_life_days=5)

        client.post(
            "/groceries/add",
            data={
                "name": "Orange Juice",
                "status": "Need",
                "shelf_life_days": "14",
            },
            follow_redirects=True,
        )

        with app.app_context():
            item = Grocery.query.filter_by(
                profile_id="TestUser", name="Orange Juice"
            ).first()
            assert item.shelf_life_days == 14


# ---------------------------------------------------------------------------
# edit route — shelf_life_days update
# ---------------------------------------------------------------------------

class TestEditRoute:

    def test_edit_updates_shelf_life_days(self, client, app, grocery_factory):
        """POST /groceries/<id>/edit should update shelf_life_days."""
        item_id = grocery_factory(name="Bread", shelf_life_days=3)

        response = client.post(
            f"/groceries/{item_id}/edit",
            data={
                "name": "Bread",
                "status": "Need",
                "shelf_life_days": "10",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        with app.app_context():
            item = _db.session.get(Grocery, item_id)
            assert item.shelf_life_days == 10

    def test_edit_can_clear_shelf_life_days(self, client, app, grocery_factory):
        """Submitting an empty shelf_life_days should set it back to None."""
        item_id = grocery_factory(name="Cheddar", shelf_life_days=21)

        client.post(
            f"/groceries/{item_id}/edit",
            data={
                "name": "Cheddar",
                "status": "Have",
                "shelf_life_days": "",  # empty string → None via _int()
            },
            follow_redirects=True,
        )

        with app.app_context():
            item = _db.session.get(Grocery, item_id)
            assert item.shelf_life_days is None

    def test_edit_shelf_life_days_persists_across_other_field_changes(
        self, client, app, grocery_factory
    ):
        """shelf_life_days should be retained when other fields are edited."""
        item_id = grocery_factory(name="Strawberries", shelf_life_days=5, category="Produce")

        client.post(
            f"/groceries/{item_id}/edit",
            data={
                "name": "Strawberries",
                "status": "Need",
                "category": "Fruit",          # changed
                "shelf_life_days": "5",        # unchanged
            },
            follow_redirects=True,
        )

        with app.app_context():
            item = _db.session.get(Grocery, item_id)
            assert item.shelf_life_days == 5
            assert item.category == "Fruit"
