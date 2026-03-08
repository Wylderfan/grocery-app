from flask import Blueprint, render_template, redirect, url_for, request, flash

from app import db
from app.models import Grocery
from app.utils.helpers import current_profile, _float

groceries_bp = Blueprint("groceries", __name__)

VALID_STATUSES = ("Need", "Have", "Out")


@groceries_bp.route("/")
def index():
    """List groceries for the current profile with optional status filter."""
    profile = current_profile()
    status_filter = request.args.get("status", "").strip()

    query = Grocery.query.filter_by(profile_id=profile)
    if status_filter in VALID_STATUSES:
        query = query.filter_by(status=status_filter)

    groceries = query.order_by(Grocery.category, Grocery.name).all()
    return render_template(
        "groceries/index.html", groceries=groceries, status_filter=status_filter
    )


@groceries_bp.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        profile  = current_profile()
        name     = request.form.get("name",     "").strip()
        quantity = _float(request.form.get("quantity", ""))
        unit     = request.form.get("unit",     "").strip() or None
        category = request.form.get("category", "").strip() or None
        status   = request.form.get("status",   "Need").strip()

        if not name:
            flash("Name is required.", "error")
            return redirect(url_for("groceries.add"))

        if status not in VALID_STATUSES:
            status = "Need"

        item = Grocery(
            profile_id=profile, name=name, quantity=quantity,
            unit=unit, category=category, status=status,
        )
        db.session.add(item)
        try:
            db.session.commit()
            flash(f"'{item.name}' added.", "success")
            return redirect(url_for("groceries.index"))
        except Exception:
            db.session.rollback()
            flash("Something went wrong. Please try again.", "error")
            return redirect(url_for("groceries.add"))

    return render_template("groceries/add.html")


@groceries_bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
def edit(item_id):
    profile = current_profile()
    item = Grocery.query.filter_by(id=item_id, profile_id=profile).first_or_404()

    if request.method == "POST":
        name     = request.form.get("name",     "").strip()
        quantity = _float(request.form.get("quantity", ""))
        unit     = request.form.get("unit",     "").strip() or None
        category = request.form.get("category", "").strip() or None
        status   = request.form.get("status",   "Need").strip()

        if not name:
            flash("Name is required.", "error")
            return redirect(url_for("groceries.edit", item_id=item_id))

        if status not in VALID_STATUSES:
            status = "Need"

        item.name     = name
        item.quantity = quantity
        item.unit     = unit
        item.category = category
        item.status   = status

        try:
            db.session.commit()
            flash(f"'{item.name}' updated.", "success")
            return redirect(url_for("groceries.index"))
        except Exception:
            db.session.rollback()
            flash("Something went wrong. Please try again.", "error")
            return redirect(url_for("groceries.edit", item_id=item_id))

    return render_template("groceries/edit.html", item=item)


@groceries_bp.route("/<int:item_id>/delete", methods=["POST"])
def delete(item_id):
    profile = current_profile()
    item = Grocery.query.filter_by(id=item_id, profile_id=profile).first_or_404()
    name = item.name
    db.session.delete(item)
    try:
        db.session.commit()
        flash(f"'{name}' deleted.", "success")
    except Exception:
        db.session.rollback()
        flash("Could not delete. Please try again.", "error")
    return redirect(url_for("groceries.index"))


@groceries_bp.route("/bulk-need", methods=["POST"])
def bulk_need():
    """Mark all checked grocery items back to 'Need'."""
    profile = current_profile()
    raw_ids = request.form.getlist("item_ids")
    ids = [int(i) for i in raw_ids if i.isdigit()]
    if ids:
        Grocery.query.filter(
            Grocery.profile_id == profile,
            Grocery.id.in_(ids),
        ).update({"status": "Need"}, synchronize_session=False)
        try:
            db.session.commit()
            flash(f"{len(ids)} item(s) marked as Need.", "success")
        except Exception:
            db.session.rollback()
            flash("Something went wrong.", "error")
    return redirect(url_for("groceries.index"))
