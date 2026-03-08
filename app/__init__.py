import os

from flask import Flask, render_template, session
from flask_sqlalchemy import SQLAlchemy
from config import config

db = SQLAlchemy()


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)

    # Import models before any db.create_all() call so SQLAlchemy registers
    # them in its metadata. This import is intentionally side-effect only.
    from app import models  # noqa: F401

    # --- Blueprint registration ---
    # Each blueprint owns a URL prefix and a folder of templates.
    # To add a feature: create app/blueprints/myfeature.py, import it here,
    # register it, and add a nav link in base.html.
    from app.blueprints.main      import main_bp
    from app.blueprints.groceries import groceries_bp
    from app.blueprints.recipes   import recipes_bp
    from app.blueprints.macros    import macros_bp
    from app.blueprints.api       import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(groceries_bp, url_prefix="/groceries")
    app.register_blueprint(recipes_bp,   url_prefix="/recipes")
    app.register_blueprint(macros_bp,    url_prefix="/macros")
    app.register_blueprint(api_bp,       url_prefix="/api")

    # --- CLI commands ---
    from app.seeds  import seed_command
    from app.backup import backup_command, restore_command

    app.cli.add_command(seed_command)
    app.cli.add_command(backup_command)
    app.cli.add_command(restore_command)

    # --- Context processor ---
    # Injects current_profile (str) and profiles (list) into every template
    # so the nav profile switcher and any per-profile logic work everywhere.
    @app.context_processor
    def inject_profile():
        profiles = app.config["PROFILES"]
        current  = session.get("profile")
        if current not in profiles:
            current = profiles[0]
        return {"current_profile": current, "profiles": profiles}

    # --- Error handlers ---
    # Render a branded error page instead of the default Flask HTML response.
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    return app
