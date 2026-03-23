from flask import Blueprint, render_template, redirect, url_for, request, flash

from app import db
from app.models import Recipe, RecipeIngredient, Grocery, MacroEntry
from app.utils.helpers import current_profile, _int, _float

recipes_bp = Blueprint("recipes", __name__)

VALID_STATUSES = ("Active", "Archived")


@recipes_bp.route("/")
def index():
    """List recipes with optional category filter."""
    profile = current_profile()
    category_filter = request.args.get("category", "").strip()

    query = Recipe.query.filter_by(profile_id=profile)
    if category_filter:
        query = query.filter_by(category=category_filter)

    recipes = query.order_by(Recipe.name).all()

    # Distinct categories for the filter bar
    rows = (
        db.session.query(Recipe.category)
        .filter(Recipe.profile_id == profile, Recipe.category.isnot(None))
        .distinct()
        .all()
    )
    all_categories = sorted(r[0] for r in rows)

    return render_template(
        "recipes/index.html",
        recipes=recipes,
        category_filter=category_filter,
        all_categories=all_categories,
    )


@recipes_bp.route("/<int:recipe_id>")
def view(recipe_id):
    """Detail view — shows ingredients, macro log stats, and instructions."""
    profile = current_profile()
    recipe  = Recipe.query.filter_by(id=recipe_id, profile_id=profile).first_or_404()

    # Aggregate macros from all log entries that used this recipe
    entries = MacroEntry.query.filter_by(profile_id=profile, recipe_id=recipe_id).all()
    log_count = len(entries)
    log_sum = None
    if log_count:
        # TODO make this fetch from recipe entry in db once macro columns are added
        log_sum = {
            "calories":  round(sum(e.calories  or 0 for e in entries), 1),
            "protein_g": round(sum(e.protein_g or 0 for e in entries), 1),
            "carbs_g":   round(sum(e.carbs_g   or 0 for e in entries), 1),
            "fat_g":     round(sum(e.fat_g     or 0 for e in entries), 1),
        }

    return render_template(
        "recipes/view.html", recipe=recipe, log_count=log_count, log_sum=log_sum
    )


@recipes_bp.route("/add", methods=["GET", "POST"])
def add():
    profile   = current_profile()
    groceries = Grocery.query.filter_by(profile_id=profile).order_by(Grocery.name).all()

    if request.method == "POST":
        name         = request.form.get("name",         "").strip()
        description  = request.form.get("description",  "").strip() or None
        servings     = _int(request.form.get("servings",      ""))
        prep_time    = _int(request.form.get("prep_time_min", ""))
        cook_time    = _int(request.form.get("cook_time_min", ""))
        instructions = request.form.get("instructions", "").strip() or None
        category     = request.form.get("category",     "").strip() or None
        rating       = _int(request.form.get("rating",  ""))
        status       = request.form.get("status",       "Active").strip()

        if not name:
            flash("Name is required.", "error")
            return redirect(url_for("recipes.add"))

        if status not in VALID_STATUSES:
            status = "Active"

        recipe = Recipe(
            profile_id=profile, name=name, description=description,
            servings=servings, prep_time_min=prep_time, cook_time_min=cook_time,
            instructions=instructions, category=category, rating=rating, status=status,
        )
        db.session.add(recipe)
        db.session.flush()  # get recipe.id before adding ingredients

        _save_ingredients(recipe.id, profile)

        try:
            db.session.commit()
            flash(f"'{recipe.name}' added.", "success")
            return redirect(url_for("recipes.index"))
        except Exception:
            db.session.rollback()
            flash("Something went wrong. Please try again.", "error")
            return redirect(url_for("recipes.add"))

    return render_template("recipes/add.html", groceries=groceries)


@recipes_bp.route("/<int:recipe_id>/edit", methods=["GET", "POST"])
def edit(recipe_id):
    profile   = current_profile()
    recipe    = Recipe.query.filter_by(id=recipe_id, profile_id=profile).first_or_404()
    groceries = Grocery.query.filter_by(profile_id=profile).order_by(Grocery.name).all()

    if request.method == "POST":
        name         = request.form.get("name",         "").strip()
        description  = request.form.get("description",  "").strip() or None
        servings     = _int(request.form.get("servings",      ""))
        prep_time    = _int(request.form.get("prep_time_min", ""))
        cook_time    = _int(request.form.get("cook_time_min", ""))
        instructions = request.form.get("instructions", "").strip() or None
        category     = request.form.get("category",     "").strip() or None
        rating       = _int(request.form.get("rating",  ""))
        status       = request.form.get("status",       "Active").strip()

        if not name:
            flash("Name is required.", "error")
            return redirect(url_for("recipes.edit", recipe_id=recipe_id))

        if status not in VALID_STATUSES:
            status = "Active"

        recipe.name          = name
        recipe.description   = description
        recipe.servings      = servings
        recipe.prep_time_min = prep_time
        recipe.cook_time_min = cook_time
        recipe.instructions  = instructions
        recipe.category      = category
        recipe.rating        = rating
        recipe.status        = status

        # Replace all ingredients with the submitted set
        RecipeIngredient.query.filter_by(recipe_id=recipe.id).delete()
        _save_ingredients(recipe.id, profile)

        try:
            db.session.commit()
            flash(f"'{recipe.name}' updated.", "success")
            return redirect(url_for("recipes.index"))
        except Exception:
            db.session.rollback()
            flash("Something went wrong. Please try again.", "error")
            return redirect(url_for("recipes.edit", recipe_id=recipe_id))

    return render_template("recipes/edit.html", recipe=recipe, groceries=groceries)


@recipes_bp.route("/<int:recipe_id>/delete", methods=["POST"])
def delete(recipe_id):
    profile = current_profile()
    recipe  = Recipe.query.filter_by(id=recipe_id, profile_id=profile).first_or_404()
    name    = recipe.name
    db.session.delete(recipe)
    try:
        db.session.commit()
        flash(f"'{name}' deleted.", "success")
    except Exception:
        db.session.rollback()
        flash("Could not delete the recipe. Please try again.", "error")
    return redirect(url_for("recipes.index"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_ingredients(recipe_id, profile):
    """Read ingredient form arrays and add RecipeIngredient rows to the session."""
    ing_names = request.form.getlist("ing_name")
    ing_qtys  = request.form.getlist("ing_qty")
    ing_units = request.form.getlist("ing_unit")
    ing_grocs = request.form.getlist("ing_grocery_id")

    for i, raw_name in enumerate(ing_names):
        name = raw_name.strip()
        if not name:
            continue
        grocery_id = _int(ing_grocs[i] if i < len(ing_grocs) else "")
        db.session.add(RecipeIngredient(
            profile_id = profile,
            recipe_id  = recipe_id,
            grocery_id = grocery_id,
            name       = name,
            quantity   = _float(ing_qtys[i]  if i < len(ing_qtys)  else ""),
            unit       = (ing_units[i].strip() if i < len(ing_units) else "") or None,
        ))
