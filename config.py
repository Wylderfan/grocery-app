import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    # Session signing key — set to a long random string in production
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "change-me")

    # Full DB connection string. Examples:
    #   MySQL:  mysql+pymysql://user:password@host/dbname
    #   SQLite: sqlite:///dev.db  (useful for local testing without a MySQL server)
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")

    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Suppress deprecation warning

    # App name displayed in nav and page titles — set APP_NAME in .env
    APP_NAME = os.environ.get("APP_NAME", "My App")

    # Comma-separated list of profile names, e.g. "Alice,Bob"
    # Single profile hides the profile switcher in the nav.
    PROFILES = [
        p.strip()
        for p in os.environ.get("PROFILES", "Player 1").split(",")
        if p.strip()
    ]


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


# Keyed by the FLASK_ENV environment variable (defaults to "development")
config = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}
