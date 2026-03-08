import os
from datetime import date, timedelta

import click
from flask.cli import with_appcontext

from app import db
from app.models import Grocery, Recipe, RecipeIngredient, MacroEntry


@click.command("seed")
@with_appcontext
def seed_command():
    """Wipe and re-seed the database with grocery, recipe, and macro data."""
    profiles_env = os.environ.get("PROFILES", "Player 1")
    profiles = [p.strip() for p in profiles_env.split(",") if p.strip()]

    click.echo("Clearing existing data...")
    MacroEntry.query.delete()
    RecipeIngredient.query.delete()
    Recipe.query.delete()
    Grocery.query.delete()
    db.session.commit()

    today     = date.today()
    yesterday = today - timedelta(days=1)

    for profile in profiles:
        click.echo(f"  Seeding profile: {profile}")

        # ── Groceries ────────────────────────────────────────────────────────
        grocery_rows = [
            ("Chicken Breast",  2.0,  "lbs",    "Meat",      "Need"),
            ("Brown Rice",      1.0,  "bag",     "Pantry",    "Have"),
            ("Broccoli",        1.0,  "head",    "Produce",   "Need"),
            ("Eggs",           12.0,  "each",    "Dairy",     "Have"),
            ("Greek Yogurt",   32.0,  "oz",      "Dairy",     "Need"),
            ("Olive Oil",       1.0,  "bottle",  "Pantry",    "Have"),
            ("Salmon Fillet",   1.0,  "lbs",     "Seafood",   "Need"),
            ("Spinach",         5.0,  "oz",      "Produce",   "Need"),
            ("Oats",            1.0,  "bag",     "Pantry",    "Have"),
            ("Bananas",         1.0,  "bunch",   "Produce",   "Out"),
        ]
        G = {}  # name → Grocery instance
        for name, qty, unit, cat, status in grocery_rows:
            g = Grocery(
                profile_id=profile, name=name,
                quantity=qty, unit=unit, category=cat, status=status,
            )
            db.session.add(g)
            db.session.flush()
            G[name] = g

        # ── Recipes ───────────────────────────────────────────────────────────

        # Recipe 1 — Grilled Chicken & Rice
        r1 = Recipe(
            profile_id=profile,
            name="Grilled Chicken & Rice",
            description="Simple high-protein dinner with grilled chicken and brown rice.",
            servings=2, prep_time_min=10, cook_time_min=25,
            instructions=(
                "1. Season chicken with salt, pepper, and olive oil.\n"
                "2. Grill 6–7 min per side until cooked through.\n"
                "3. Cook rice per package directions.\n"
                "4. Serve together."
            ),
            category="Dinner", rating=5, status="Active",
        )
        db.session.add(r1)
        db.session.flush()
        for name, qty, unit, gname in [
            ("Chicken Breast", 1.0, "lbs",  "Chicken Breast"),
            ("Brown Rice",     0.5, "cup",  "Brown Rice"),
            ("Olive Oil",      1.0, "tbsp", "Olive Oil"),
        ]:
            db.session.add(RecipeIngredient(
                profile_id=profile, recipe_id=r1.id,
                grocery_id=G[gname].id, name=name, quantity=qty, unit=unit,
            ))

        # Recipe 2 — Salmon & Spinach
        r2 = Recipe(
            profile_id=profile,
            name="Salmon & Spinach",
            description="Omega-3 rich salmon over sautéed garlic spinach.",
            servings=1, prep_time_min=5, cook_time_min=15,
            instructions=(
                "1. Pat salmon dry and season with salt and pepper.\n"
                "2. Pan-sear in olive oil, 4–5 min per side.\n"
                "3. Sauté spinach with a pinch of garlic in same pan.\n"
                "4. Plate together."
            ),
            category="Dinner", rating=4, status="Active",
        )
        db.session.add(r2)
        db.session.flush()
        for name, qty, unit, gname in [
            ("Salmon Fillet", 6.0, "oz",   "Salmon Fillet"),
            ("Spinach",       2.0, "cups", "Spinach"),
            ("Olive Oil",     1.0, "tbsp", "Olive Oil"),
        ]:
            db.session.add(RecipeIngredient(
                profile_id=profile, recipe_id=r2.id,
                grocery_id=G[gname].id, name=name, quantity=qty, unit=unit,
            ))

        # Recipe 3 — Overnight Oats
        r3 = Recipe(
            profile_id=profile,
            name="Overnight Oats",
            description="Prep the night before for a quick high-protein breakfast.",
            servings=1, prep_time_min=5, cook_time_min=0,
            instructions=(
                "1. Combine oats and Greek yogurt in a jar.\n"
                "2. Add sliced banana.\n"
                "3. Refrigerate overnight.\n"
                "4. Top with any extras and serve cold."
            ),
            category="Breakfast", rating=4, status="Active",
        )
        db.session.add(r3)
        db.session.flush()
        for name, qty, unit, gname in [
            ("Oats",         0.5, "cup",  "Oats"),
            ("Greek Yogurt", 0.5, "cup",  "Greek Yogurt"),
            ("Bananas",      1.0, "each", "Bananas"),
        ]:
            db.session.add(RecipeIngredient(
                profile_id=profile, recipe_id=r3.id,
                grocery_id=G[gname].id, name=name, quantity=qty, unit=unit,
            ))

        # Recipe 4 — Scrambled Eggs & Veggies
        r4 = Recipe(
            profile_id=profile,
            name="Scrambled Eggs & Veggies",
            description="Quick protein-packed breakfast scramble.",
            servings=1, prep_time_min=5, cook_time_min=10,
            instructions=(
                "1. Whisk 3 eggs with a pinch of salt.\n"
                "2. Sauté spinach in olive oil for 2 min.\n"
                "3. Add eggs and scramble over medium heat to desired doneness."
            ),
            category="Breakfast", rating=3, status="Active",
        )
        db.session.add(r4)
        db.session.flush()
        for name, qty, unit, gname in [
            ("Eggs",      3.0, "each",  "Eggs"),
            ("Spinach",   1.0, "cup",   "Spinach"),
            ("Olive Oil", 0.5, "tbsp",  "Olive Oil"),
        ]:
            db.session.add(RecipeIngredient(
                profile_id=profile, recipe_id=r4.id,
                grocery_id=G[gname].id, name=name, quantity=qty, unit=unit,
            ))

        # ── Macro entries — yesterday ─────────────────────────────────────────
        for meal, fname, rid, cal, prot, carbs, fat in [
            ("Breakfast", None,              r3.id, 380, 18, 52,  8),
            ("Lunch",     "Turkey Sandwich", None,  450, 32, 45, 12),
            ("Dinner",    None,              r1.id, 620, 52, 48, 14),
            ("Snack",     "Protein Bar",     None,  210, 20, 22,  5),
        ]:
            db.session.add(MacroEntry(
                profile_id=profile, date=yesterday,
                meal_label=meal, recipe_id=rid, food_name=fname,
                calories=cal, protein_g=prot, carbs_g=carbs, fat_g=fat,
            ))

        # ── Macro entries — today ─────────────────────────────────────────────
        for meal, fname, rid, cal, prot, carbs, fat in [
            ("Breakfast", None, r4.id, 310, 24,  8, 18),
            ("Lunch",     None, r2.id, 480, 44,  6, 28),
        ]:
            db.session.add(MacroEntry(
                profile_id=profile, date=today,
                meal_label=meal, recipe_id=rid, food_name=fname,
                calories=cal, protein_g=prot, carbs_g=carbs, fat_g=fat,
            ))

    db.session.commit()
    click.echo(f"Done. Seeded {len(profiles)} profile(s) with groceries, recipes, and macro entries.")
