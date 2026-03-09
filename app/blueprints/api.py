"""
JSON REST API blueprint — all routes return/accept JSON, no HTML.

Profile is read from the ?profile= query param; defaults to the first configured profile.
"""
from datetime import date

from flask import Blueprint, jsonify, request, current_app

from app import db
from app.models import Grocery, Recipe, MacroEntry
from app.utils.helpers import _float, _int

api_bp = Blueprint("api", __name__)


def _profile():
    """Return the active profile from ?profile= param, defaulting to the first."""
    profiles = current_app.config["PROFILES"]
    p = request.args.get("profile", "").strip()
    return p if p in profiles else profiles[0]


def _parse_date(s):
    try:
        return date.fromisoformat(s) if s else date.today()
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Groceries
# ---------------------------------------------------------------------------

@api_bp.route("/groceries")
def list_groceries():
    """GET /api/groceries — list all groceries, supports ?status= filter."""
    profile       = _profile()
    status_filter = request.args.get("status", "").strip()
    query         = Grocery.query.filter_by(profile_id=profile)
    if status_filter in ("Need", "Have"):
        query = query.filter_by(status=status_filter)
    items = query.order_by(Grocery.category, Grocery.name).all()
    return jsonify([{
        "id": g.id, "name": g.name, "quantity": g.quantity,
        "unit": g.unit, "category": g.category, "status": g.status,
    } for g in items])


@api_bp.route("/groceries", methods=["POST"])
def create_grocery():
    """POST /api/groceries — create a new grocery item."""
    profile = _profile()
    data    = request.get_json() or {}
    name    = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    status = data.get("status", "Need")
    if status not in ("Need", "Have"):
        status = "Need"
    g = Grocery(
        profile_id=profile, name=name,
        quantity=_float(str(data.get("quantity", ""))),
        unit=data.get("unit") or None,
        category=data.get("category") or None,
        status=status,
    )
    db.session.add(g)
    db.session.commit()
    return jsonify({"id": g.id, "name": g.name, "status": g.status}), 201


@api_bp.route("/groceries/<int:item_id>", methods=["PATCH"])
def update_grocery(item_id):
    """PATCH /api/groceries/<id> — partial update; useful for quick status toggling."""
    profile = _profile()
    g       = Grocery.query.filter_by(id=item_id, profile_id=profile).first_or_404()
    data    = request.get_json() or {}
    if "name" in data:
        g.name = data["name"].strip() or g.name
    if "quantity" in data:
        g.quantity = _float(str(data["quantity"]))
    if "unit" in data:
        g.unit = data["unit"] or None
    if "category" in data:
        g.category = data["category"] or None
    if "status" in data and data["status"] in ("Need", "Have"):
        g.status = data["status"]
    db.session.commit()
    return jsonify({"id": g.id, "name": g.name, "status": g.status})


# ---------------------------------------------------------------------------
# Recipes
# ---------------------------------------------------------------------------

@api_bp.route("/recipes")
def list_recipes():
    """GET /api/recipes — list all active recipes."""
    profile = _profile()
    recipes = Recipe.query.filter_by(profile_id=profile).order_by(Recipe.name).all()
    return jsonify([{
        "id": r.id, "name": r.name, "category": r.category,
        "rating": r.rating, "servings": r.servings, "status": r.status,
    } for r in recipes])


@api_bp.route("/recipes/<int:recipe_id>")
def get_recipe(recipe_id):
    """GET /api/recipes/<id> — single recipe with all ingredients."""
    profile = _profile()
    r       = Recipe.query.filter_by(id=recipe_id, profile_id=profile).first_or_404()
    return jsonify({
        "id": r.id, "name": r.name, "description": r.description,
        "servings": r.servings, "prep_time_min": r.prep_time_min,
        "cook_time_min": r.cook_time_min, "instructions": r.instructions,
        "category": r.category, "rating": r.rating, "status": r.status,
        "ingredients": [{
            "id": ing.id, "name": ing.name,
            "quantity": ing.quantity, "unit": ing.unit,
            "grocery_id": ing.grocery_id,
        } for ing in r.ingredients],
    })


# ---------------------------------------------------------------------------
# Macros
# ---------------------------------------------------------------------------

@api_bp.route("/macros")
def list_macros():
    """GET /api/macros?date=YYYY-MM-DD — entries for a day with totals."""
    profile   = _profile()
    view_date = _parse_date(request.args.get("date", ""))
    if view_date is None:
        return jsonify({"error": "invalid date format, use YYYY-MM-DD"}), 400

    entries = (
        MacroEntry.query
        .filter_by(profile_id=profile, date=view_date)
        .order_by(MacroEntry.created_at)
        .all()
    )
    items = [{
        "id": e.id, "date": e.date.isoformat(), "meal_label": e.meal_label,
        "recipe_id": e.recipe_id, "food_name": e.food_name,
        "calories": e.calories, "protein_g": e.protein_g,
        "carbs_g": e.carbs_g, "fat_g": e.fat_g, "notes": e.notes,
    } for e in entries]
    totals = {
        "calories":  sum(e.calories  or 0 for e in entries),
        "protein_g": sum(e.protein_g or 0 for e in entries),
        "carbs_g":   sum(e.carbs_g   or 0 for e in entries),
        "fat_g":     sum(e.fat_g     or 0 for e in entries),
    }
    return jsonify({"date": view_date.isoformat(), "entries": items, "totals": totals})


@api_bp.route("/macros", methods=["POST"])
def create_macro():
    """POST /api/macros — create a macro log entry."""
    profile = _profile()
    data    = request.get_json() or {}

    entry_date = _parse_date(data.get("date", ""))
    if entry_date is None:
        return jsonify({"error": "invalid date format, use YYYY-MM-DD"}), 400

    food_name = data.get("food_name") or None
    recipe_id = _int(str(data["recipe_id"])) if data.get("recipe_id") else None
    if not food_name and not recipe_id:
        return jsonify({"error": "food_name or recipe_id is required"}), 400

    entry = MacroEntry(
        profile_id=profile, date=entry_date,
        meal_label=data.get("meal_label") or None,
        recipe_id=recipe_id, food_name=food_name,
        calories=_float(str(data.get("calories", ""))),
        protein_g=_float(str(data.get("protein_g", ""))),
        carbs_g=_float(str(data.get("carbs_g", ""))),
        fat_g=_float(str(data.get("fat_g", ""))),
        notes=data.get("notes") or None,
    )
    db.session.add(entry)
    db.session.commit()
    return jsonify({"id": entry.id, "date": entry.date.isoformat()}), 201
