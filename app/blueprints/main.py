from datetime import date

from flask import Blueprint, render_template, request, session, redirect, current_app

from app.models import Grocery, Recipe, MacroEntry
from app.utils.helpers import current_profile

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Dashboard — stat cards + grocery needs + today's macro summary."""
    profile = current_profile()
    today   = date.today()

    # Stat cards
    groceries_needed = Grocery.query.filter_by(profile_id=profile, status="Need").count()
    recipes_count    = Recipe.query.filter_by(profile_id=profile, status="Active").count()

    today_entries  = MacroEntry.query.filter_by(profile_id=profile, date=today).all()
    today_calories = sum(e.calories  or 0 for e in today_entries)
    today_protein  = sum(e.protein_g or 0 for e in today_entries)

    # Grocery shopping list preview — items still needed
    needed_groceries = (
        Grocery.query
        .filter_by(profile_id=profile, status="Need")
        .order_by(Grocery.category, Grocery.name)
        .limit(8)
        .all()
    )

    return render_template(
        "main/index.html",
        groceries_needed  = groceries_needed,
        recipes_count     = recipes_count,
        today_calories    = today_calories,
        today_protein     = today_protein,
        needed_groceries  = needed_groceries,
        today_entries     = today_entries,
        today             = today,
    )


@main_bp.route("/switch-profile", methods=["POST"])
def switch_profile():
    """Switch the active profile. Stores the selection in the Flask session."""
    profiles = current_app.config["PROFILES"]
    name = request.form.get("profile", "").strip()
    if name in profiles:
        session["profile"] = name
    return redirect(request.referrer or "/")
