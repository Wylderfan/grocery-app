from datetime import datetime

from app import db


class Item(db.Model):
    """Example model — copy this to add your own domain models.

    Each field demonstrates a specific UI/data pattern.
    See PATTERNS.md for step-by-step guidance on reusing each pattern.
    """

    __tablename__ = "items"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Profile scoping — required on every model.
    # Always filter queries: Item.query.filter_by(profile_id=profile)
    profile_id = db.Column(db.String(100), nullable=False)

    # Demonstrates: required text input pattern
    name = db.Column(db.String(200), nullable=False)

    # Demonstrates: optional textarea pattern
    # Use db.Text (unbounded) for long-form / multi-line content.
    # nullable=True means the field is optional — store None when blank.
    description = db.Column(db.Text, nullable=True)

    # Demonstrates: star-rating pattern
    # Integer 1–5; nullable means "not yet rated" (renders as empty stars).
    # Paired with the .star-btn widget in base.html and the stars() macro in macros.html.
    priority = db.Column(db.Integer, nullable=True)

    # Demonstrates: enum / status-badge pattern
    # Fixed set of string values; color-coded in templates with if/elif branches.
    # To add a new value: update the Enum() list here, add a badge branch in templates,
    # then run a migration (or db.create_all() on a fresh DB).
    status = db.Column(
        db.Enum("Active", "Done", "Archived", name="itemstatus"),
        nullable=False,
        default="Active",
    )

    # Demonstrates: free-text grouping / tag pattern
    # Good for loose, user-defined categories. For a strict fixed set,
    # use a FK to a separate Category model instead.
    category = db.Column(db.String(100), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def __repr__(self) -> str:
        return f"<Item profile={self.profile_id!r} name={self.name!r} status={self.status!r}>"
