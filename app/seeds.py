import os

import click
from flask.cli import with_appcontext

from app import db
from app.models import Item

# Six seed items with varied statuses, priorities, categories, and descriptions.
# This populates the app on first load so every visual pattern is visible immediately.
SEED_ITEMS = [
    {
        "name":        "Set up the project",
        "description": "Clone the repo, fill in .env, run db.create_all(), then flask seed.",
        "priority":    5,
        "status":      "Done",
        "category":    "Setup",
    },
    {
        "name":        "Read PATTERNS.md",
        "description": "Quick-reference cheat sheet for every pattern in this codebase.",
        "priority":    4,
        "status":      "Done",
        "category":    "Setup",
    },
    {
        "name":        "Replace the Item model",
        "description": "Add your own domain fields. Copy the pattern comments from models.py.",
        "priority":    5,
        "status":      "Active",
        "category":    "Development",
    },
    {
        "name":        "Add a new blueprint",
        "description": "Copy items.py, rename it, register it in app/__init__.py.",
        "priority":    3,
        "status":      "Active",
        "category":    "Development",
    },
    {
        "name":        "Configure Tailscale binding",
        "description": "Set TAILSCALE_IP in .env. Use python run.py, not flask run.",
        "priority":    2,
        "status":      "Active",
        "category":    "Deployment",
    },
    {
        "name":        "Deploy with systemd",
        "description": "Edit deploy/flask-starter.service and copy to /etc/systemd/system/.",
        "priority":    None,
        "status":      "Archived",
        "category":    "Deployment",
    },
]


@click.command("seed")
@with_appcontext
def seed_command():
    """Wipe and re-seed the database with example items for all profiles."""
    profiles_env = os.environ.get("PROFILES", "Player 1")
    profiles = [p.strip() for p in profiles_env.split(",") if p.strip()]

    click.echo("Clearing existing data...")
    Item.query.delete()
    db.session.commit()

    click.echo(f"Seeding {len(SEED_ITEMS)} items for {len(profiles)} profile(s): {profiles}...")
    for profile in profiles:
        for data in SEED_ITEMS:
            db.session.add(Item(profile_id=profile, **data))
    db.session.commit()

    click.echo(f"Done. {len(SEED_ITEMS)} items seeded per profile.")
