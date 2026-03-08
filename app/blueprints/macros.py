from datetime import date, timedelta

from flask import Blueprint, render_template, redirect, url_for, request, flash

from app import db
from app.models import MacroEntry, Recipe
from app.utils.helpers import current_profile, _float, _int

macros_bp = Blueprint("macros", __name__)


def _parse_date(date_str):
    try:
        return date.fromisoformat(date_str) if date_str else date.today()
    except ValueError:
        return date.today()


@macros_bp.route("/")
def index():
    """Daily macro log — shows one day at a time with totals row."""
    profile   = current_profile()
    view_date = _parse_date(request.args.get("date", ""))

    entries = (
        MacroEntry.query
        .filter_by(profile_id=profile, date=view_date)
        .order_by(MacroEntry.created_at)
        .all()
    )

    totals = {
        "calories":  round(sum(e.calories  or 0 for e in entries), 1),
        "protein_g": round(sum(e.protein_g or 0 for e in entries), 1),
        "carbs_g":   round(sum(e.carbs_g   or 0 for e in entries), 1),
        "fat_g":     round(sum(e.fat_g     or 0 for e in entries), 1),
    }

    prev_date = view_date - timedelta(days=1)
    next_date = view_date + timedelta(days=1)

    return render_template(
        "macros/index.html",
        entries   = entries,
        view_date = view_date,
        today     = date.today(),
        totals    = totals,
        prev_date = prev_date,
        next_date = next_date,
    )


@macros_bp.route("/add", methods=["GET", "POST"])
def add():
    profile  = current_profile()
    recipes  = (
        Recipe.query
        .filter_by(profile_id=profile, status="Active")
        .order_by(Recipe.name)
        .all()
    )
    date_str = request.args.get("date", str(date.today()))

    if request.method == "POST":
        entry_date = _parse_date(request.form.get("date", ""))
        meal_label = request.form.get("meal_label", "").strip() or None
        recipe_id  = _int(request.form.get("recipe_id", ""))
        food_name  = request.form.get("food_name", "").strip() or None
        calories   = _float(request.form.get("calories",  ""))
        protein_g  = _float(request.form.get("protein_g", ""))
        carbs_g    = _float(request.form.get("carbs_g",   ""))
        fat_g      = _float(request.form.get("fat_g",     ""))
        notes      = request.form.get("notes", "").strip() or None

        if not food_name and not recipe_id:
            flash("Enter a food name or select a recipe.", "error")
            return redirect(url_for("macros.add", date=entry_date.isoformat()))

        entry = MacroEntry(
            profile_id=profile, date=entry_date, meal_label=meal_label,
            recipe_id=recipe_id, food_name=food_name, calories=calories,
            protein_g=protein_g, carbs_g=carbs_g, fat_g=fat_g, notes=notes,
        )
        db.session.add(entry)
        try:
            db.session.commit()
            flash("Entry added.", "success")
            return redirect(url_for("macros.index", date=entry_date.isoformat()))
        except Exception:
            db.session.rollback()
            flash("Something went wrong. Please try again.", "error")
            return redirect(url_for("macros.add", date=entry_date.isoformat()))

    return render_template("macros/add.html", recipes=recipes, date_str=date_str)


@macros_bp.route("/<int:entry_id>/edit", methods=["GET", "POST"])
def edit(entry_id):
    profile = current_profile()
    entry   = MacroEntry.query.filter_by(id=entry_id, profile_id=profile).first_or_404()
    recipes = (
        Recipe.query
        .filter_by(profile_id=profile, status="Active")
        .order_by(Recipe.name)
        .all()
    )

    if request.method == "POST":
        entry_date = _parse_date(request.form.get("date", ""))
        meal_label = request.form.get("meal_label", "").strip() or None
        recipe_id  = _int(request.form.get("recipe_id", ""))
        food_name  = request.form.get("food_name", "").strip() or None
        calories   = _float(request.form.get("calories",  ""))
        protein_g  = _float(request.form.get("protein_g", ""))
        carbs_g    = _float(request.form.get("carbs_g",   ""))
        fat_g      = _float(request.form.get("fat_g",     ""))
        notes      = request.form.get("notes", "").strip() or None

        entry.date       = entry_date
        entry.meal_label = meal_label
        entry.recipe_id  = recipe_id
        entry.food_name  = food_name
        entry.calories   = calories
        entry.protein_g  = protein_g
        entry.carbs_g    = carbs_g
        entry.fat_g      = fat_g
        entry.notes      = notes

        try:
            db.session.commit()
            flash("Entry updated.", "success")
            return redirect(url_for("macros.index", date=entry_date.isoformat()))
        except Exception:
            db.session.rollback()
            flash("Something went wrong. Please try again.", "error")
            return redirect(url_for("macros.edit", entry_id=entry_id))

    return render_template("macros/edit.html", entry=entry, recipes=recipes)


@macros_bp.route("/<int:entry_id>/delete", methods=["POST"])
def delete(entry_id):
    profile    = current_profile()
    entry      = MacroEntry.query.filter_by(id=entry_id, profile_id=profile).first_or_404()
    entry_date = entry.date
    db.session.delete(entry)
    try:
        db.session.commit()
        flash("Entry deleted.", "success")
    except Exception:
        db.session.rollback()
        flash("Could not delete the entry. Please try again.", "error")
    return redirect(url_for("macros.index", date=entry_date.isoformat()))
