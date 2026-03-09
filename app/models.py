from datetime import datetime, date

from app import db


class Grocery(db.Model):
    """A grocery list item — tracks what to buy, have on hand, or is out."""

    __tablename__ = "groceries"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Profile scoping — required on every model.
    profile_id = db.Column(db.String(100), nullable=False)

    name     = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Float, nullable=True)         # e.g. 2.0
    unit     = db.Column(db.String(50),  nullable=True)   # e.g. "lbs", "oz", "each"
    category = db.Column(db.String(100), nullable=True)   # e.g. "Produce", "Dairy", "Meat"

    status = db.Column(
        db.Enum("Need", "Have", name="grocerystatus"),
        nullable=False,
        default="Need",
    )

    # Macros per 1 of this item's unit (e.g. per 1 lbs, per 1 cup, per 1 each).
    # The unit field is the multiplier: recipe_ingredient.quantity × these values.
    calories_per_unit = db.Column(db.Float, nullable=True)
    protein_per_unit  = db.Column(db.Float, nullable=True)
    carbs_per_unit    = db.Column(db.Float, nullable=True)
    fat_per_unit      = db.Column(db.Float, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    recipe_ingredients = db.relationship("RecipeIngredient", backref="grocery", lazy=True)

    def __repr__(self):
        return f"<Grocery profile={self.profile_id!r} name={self.name!r} status={self.status!r}>"


class Recipe(db.Model):
    """A recipe with metadata, ingredients, and optional star rating."""

    __tablename__ = "recipes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    profile_id = db.Column(db.String(100), nullable=False)

    name          = db.Column(db.String(200), nullable=False)
    description   = db.Column(db.Text,        nullable=True)
    servings      = db.Column(db.Integer,     nullable=True)
    prep_time_min = db.Column(db.Integer,     nullable=True)
    cook_time_min = db.Column(db.Integer,     nullable=True)
    instructions  = db.Column(db.Text,        nullable=True)
    category      = db.Column(db.String(100), nullable=True)  # e.g. "Breakfast", "Dinner"
    rating        = db.Column(db.Integer,     nullable=True)   # 1–5 star rating

    status = db.Column(
        db.Enum("Active", "Archived", name="recipestatus"),
        nullable=False,
        default="Active",
    )

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    ingredients  = db.relationship(
        "RecipeIngredient", backref="recipe", lazy=True, cascade="all, delete-orphan"
    )
    macro_entries = db.relationship("MacroEntry", backref="recipe", lazy=True)

    @property
    def computed_macros(self):
        """Sum ingredient quantity × grocery macros_per_unit across all ingredients.

        Returns a dict with cal/protein/carbs/fat totals and a 'complete' flag
        that is False when any linked grocery is missing macro data.
        """
        cal = protein = carbs = fat = 0.0
        complete = True
        for ing in self.ingredients:
            g = ing.grocery
            if g and g.calories_per_unit is not None:
                qty = ing.quantity or 0.0
                cal     += qty * (g.calories_per_unit or 0.0)
                protein += qty * (g.protein_per_unit  or 0.0)
                carbs   += qty * (g.carbs_per_unit    or 0.0)
                fat     += qty * (g.fat_per_unit      or 0.0)
            else:
                complete = False
        return {
            "calories":  round(cal,     1),
            "protein_g": round(protein, 1),
            "carbs_g":   round(carbs,   1),
            "fat_g":     round(fat,     1),
            "complete":  complete,
        }

    def __repr__(self):
        return f"<Recipe profile={self.profile_id!r} name={self.name!r}>"


class RecipeIngredient(db.Model):
    """An ingredient line in a recipe, optionally linked to a Grocery item."""

    __tablename__ = "recipe_ingredients"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    profile_id = db.Column(db.String(100), nullable=False)
    recipe_id  = db.Column(db.Integer, db.ForeignKey("recipes.id"),   nullable=False)
    grocery_id = db.Column(db.Integer, db.ForeignKey("groceries.id"), nullable=True)

    name     = db.Column(db.String(200), nullable=False)  # ingredient display name
    quantity = db.Column(db.Float,       nullable=True)
    unit     = db.Column(db.String(50),  nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<RecipeIngredient recipe_id={self.recipe_id} name={self.name!r}>"


class MacroEntry(db.Model):
    """A single meal/food entry in the daily macro log."""

    __tablename__ = "macro_entries"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    profile_id  = db.Column(db.String(100), nullable=False)
    date        = db.Column(db.Date,        nullable=False)
    meal_label  = db.Column(db.String(100), nullable=True)   # e.g. "Breakfast", "Lunch"
    recipe_id   = db.Column(db.Integer, db.ForeignKey("recipes.id"), nullable=True)
    food_name   = db.Column(db.String(200), nullable=True)   # for manual entries without a recipe
    calories    = db.Column(db.Float, nullable=True)
    protein_g   = db.Column(db.Float, nullable=True)
    carbs_g     = db.Column(db.Float, nullable=True)
    fat_g       = db.Column(db.Float, nullable=True)
    notes       = db.Column(db.Text,  nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<MacroEntry profile={self.profile_id!r} date={self.date} meal={self.meal_label!r}>"
