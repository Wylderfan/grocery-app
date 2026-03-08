from flask import Blueprint, render_template, redirect, url_for, request, flash

from app import db
from app.models import Item
from app.utils.helpers import current_profile, _int

# Blueprint registration — registered in app/__init__.py with url_prefix="/items".
# Copy this file to add a new feature: rename the blueprint, swap Item for your model,
# register it in create_app(), and create matching templates.
items_bp = Blueprint("items", __name__)

# Valid status values — mirrors the Enum in models.py.
# Keep these in sync if you add or remove enum values.
VALID_STATUSES = ("Active", "Done", "Archived")


@items_bp.route("/")
def index():
    """List all items for the current profile.

    Demonstrates: profile-scoped query + query-param filtering by an enum field.
    Copy the status_filter block to filter any list page by any field.
    """
    # Always scope queries to the active profile — never query without this
    profile = current_profile()

    # Query-param filter: ?status=Active / ?status=Done / ?status=Archived
    # Omitting the param (or an unrecognized value) shows all items.
    status_filter = request.args.get("status", "").strip()

    # Build the base query scoped to this profile
    query = Item.query.filter_by(profile_id=profile)

    # Apply the optional status filter when a valid value is provided
    if status_filter in VALID_STATUSES:
        query = query.filter_by(status=status_filter)

    items = query.order_by(Item.updated_at.desc()).all()
    return render_template("items/index.html", items=items, status_filter=status_filter)


@items_bp.route("/add", methods=["GET", "POST"])
def add():
    """Add a new item.

    Demonstrates: form handling with validation, flash messages (success/error),
    and redirect-after-POST to prevent duplicate submissions on refresh.
    """
    if request.method == "POST":
        profile = current_profile()

        # Collect and sanitize all form fields
        name        = request.form.get("name",        "").strip()
        description = request.form.get("description", "").strip() or None  # None if blank
        priority    = _int(request.form.get("priority", ""))               # None if blank
        status      = request.form.get("status",      "Active").strip()
        category    = request.form.get("category",    "").strip() or None  # None if blank

        # Validate required fields — flash("msg", "error") shows a red banner
        if not name:
            flash("Name is required.", "error")
            return redirect(url_for("items.add"))

        # Clamp status to known values to guard against form tampering
        if status not in VALID_STATUSES:
            status = "Active"

        item = Item(
            profile_id  = profile,
            name        = name,
            description = description,
            priority    = priority,
            status      = status,
            category    = category,
        )
        db.session.add(item)
        try:
            db.session.commit()
            flash(f"'{item.name}' added.", "success")  # "success" → green banner
            return redirect(url_for("items.index"))
        except Exception:
            db.session.rollback()
            flash("Something went wrong. Please try again.", "error")
            return redirect(url_for("items.add"))

    return render_template("items/add.html")


@items_bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
def edit(item_id):
    """Edit an existing item.

    Demonstrates: fetching a single record scoped to the current profile,
    pre-filling a form with existing values, and updating on POST.
    filter_by(profile_id=profile) + first_or_404() prevents cross-profile access.
    """
    profile = current_profile()
    # Profile-scoped fetch — returns 404 if item belongs to a different profile
    item = Item.query.filter_by(id=item_id, profile_id=profile).first_or_404()

    if request.method == "POST":
        name        = request.form.get("name",        "").strip()
        description = request.form.get("description", "").strip() or None
        priority    = _int(request.form.get("priority", ""))
        status      = request.form.get("status",      "Active").strip()
        category    = request.form.get("category",    "").strip() or None

        if not name:
            flash("Name is required.", "error")
            return redirect(url_for("items.edit", item_id=item_id))

        if status not in VALID_STATUSES:
            status = "Active"

        # Assign updated values directly to the ORM object — SQLAlchemy tracks changes
        item.name        = name
        item.description = description
        item.priority    = priority
        item.status      = status
        item.category    = category

        try:
            db.session.commit()
            flash(f"'{item.name}' updated.", "success")
            return redirect(url_for("items.index"))
        except Exception:
            db.session.rollback()
            flash("Something went wrong. Please try again.", "error")
            return redirect(url_for("items.edit", item_id=item_id))

    return render_template("items/edit.html", item=item)


@items_bp.route("/<int:item_id>/delete", methods=["POST"])
def delete(item_id):
    """Delete an item. POST-only to prevent accidental deletion via GET.

    Demonstrates: profile-scoped delete with a flash confirmation message.
    """
    profile = current_profile()
    item = Item.query.filter_by(id=item_id, profile_id=profile).first_or_404()
    name = item.name
    db.session.delete(item)
    try:
        db.session.commit()
        flash(f"'{name}' deleted.", "success")
    except Exception:
        db.session.rollback()
        flash("Could not delete the item. Please try again.", "error")
    return redirect(url_for("items.index"))
