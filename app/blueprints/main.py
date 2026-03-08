from flask import Blueprint, render_template, request, session, redirect, current_app

from app.models import Item
from app.utils.helpers import current_profile

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Dashboard — aggregate stats and recent items for the current profile.

    Demonstrates: multiple stat-card queries and a recent-items list.
    Copy each query pattern to add new stat cards for your own models.
    """
    profile = current_profile()

    # Stat card queries — each is a simple count scoped to this profile
    item_count   = Item.query.filter_by(profile_id=profile).count()
    active_count = Item.query.filter_by(profile_id=profile, status="Active").count()
    done_count   = Item.query.filter_by(profile_id=profile, status="Done").count()

    # Recent items preview — 5 most recently updated for the dashboard list
    recent_items = (
        Item.query
        .filter_by(profile_id=profile)
        .order_by(Item.updated_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "main/index.html",
        item_count   = item_count,
        active_count = active_count,
        done_count   = done_count,
        recent_items = recent_items,
    )


@main_bp.route("/switch-profile", methods=["POST"])
def switch_profile():
    """Switch the active profile. Stores the selection in the Flask session.

    The profile switcher in base.html posts here. The referrer redirect
    keeps the user on whichever page they were viewing.
    """
    profiles = current_app.config["PROFILES"]
    name = request.form.get("profile", "").strip()
    if name in profiles:
        session["profile"] = name
    return redirect(request.referrer or "/")
