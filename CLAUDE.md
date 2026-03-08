# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

A reusable Flask starter template. The app ships with:

- A **dashboard** (`/`) showing stat cards (total / active / done) and a recent-items list
- An **items** blueprint (`/items`) with full CRUD as a copy-paste starting point
- A **multi-profile system** — session-based, no login, profiles configured via env var
- **Tailscale-only binding** — no public exposure, no auth system needed

Replace the `Item` model and `items` blueprint with your own domain models and blueprints.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3 |
| Web Framework | Flask |
| ORM | Flask-SQLAlchemy |
| Database Driver | PyMySQL |
| Database | MySQL (SQLite works for local testing) |
| Templates | Jinja2 |
| Styling | Tailwind CSS (CDN) |
| Drag-and-Drop | SortableJS (CDN, available if needed) |
| Production Server | Gunicorn |
| Environment Vars | python-dotenv |
| Network / Auth | Tailscale |

---

## Project Structure

```
flask-starter/
├── app/
│   ├── __init__.py          # App factory — db init, blueprint + CLI registration, error handlers
│   ├── models.py            # SQLAlchemy models — each field has a comment explaining its pattern
│   ├── seeds.py             # flask seed CLI command — 6 varied items per profile
│   ├── backup.py            # flask db-backup / db-restore CLI commands
│   ├── blueprints/
│   │   ├── main.py          # Dashboard (/) with stat cards + recent items; profile switcher
│   │   └── items.py         # Example CRUD blueprint — copy this to add new features
│   ├── utils/
│   │   └── helpers.py       # current_profile(), _int(), _float()
│   └── templates/
│       ├── base.html        # Base layout — nav, Tailwind, SortableJS, profile switcher, flash msgs, star-btn JS
│       ├── macros.html      # stars(value, max=5) macro
│       ├── main/
│       │   └── index.html   # Dashboard — 3 stat cards + recent items list
│       ├── items/
│       │   ├── index.html   # Item list with filter bar, status badges, priority stars, category tags
│       │   ├── add.html     # Add item form — all field types demonstrated
│       │   └── edit.html    # Edit item form — pre-filled
│       └── errors/
│           ├── 404.html
│           └── 500.html
├── backups/                 # SQL dumps written here (gitignored except .gitkeep)
├── deploy/
│   ├── flask-starter.service   # systemd template
│   └── flask-starter.openrc    # OpenRC template
├── .env                     # Never commit — see .env.example
├── .env.example
├── .gitignore
├── config.py                # DevelopmentConfig / ProductionConfig, APP_NAME, PROFILES
├── PATTERNS.md              # Quick-reference cheat sheet for every pattern in the codebase
├── requirements.txt
└── run.py                   # Dev entry point — binds to TAILSCALE_IP
```

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in .env, then:
flask shell
>>> from app import db, models
>>> db.create_all()
flask seed
python run.py
```

For local testing without MySQL, set `DATABASE_URL=sqlite:///dev.db` in `.env`.

---

## Key Patterns

### App factory (`app/__init__.py`)
All blueprint and CLI registrations live here. When adding a new blueprint:
1. Import and register it in `create_app()`
2. Add a nav link in `base.html`

### Profile system
- `PROFILES` env var is a comma-separated list of names
- Active profile stored in `session["profile"]`
- `current_profile()` in `app/utils/helpers.py` returns the active profile, defaulting to the first
- Always filter queries by `profile_id=current_profile()`
- `inject_profile` context processor makes `current_profile` and `profiles` available in all templates
- Profile switcher in nav renders automatically when `len(profiles) > 1`

### Models (`app/models.py`)
The `Item` model demonstrates four field patterns with inline comments:
- `name` — required text input (`String`, `nullable=False`)
- `description` — optional textarea (`Text`, `nullable=True`)
- `priority` — star rating (`Integer` 1–5, `nullable=True`)
- `status` — enum/badge (`db.Enum("Active", "Done", "Archived")`, `default="Active"`)
- `category` — free-text tag (`String(100)`, `nullable=True`)

All models must have `profile_id = db.Column(db.String(100), nullable=False)`.

### Templates
- All extend `base.html`
- Dark Tailwind aesthetic: `bg-gray-950` body, `bg-gray-900` cards, `bg-gray-800` inputs
- Flash messages: `flash("message", "success")` or `flash("message", "error")`
- `config.APP_NAME` is available in all templates
- Import `stars` macro from `macros.html` for 1–5 star displays
- Status badge color convention: green = Active, blue = Done, gray = Archived/neutral

### Star rating widget
- `.star-btn` buttons in forms; JS handler in `base.html` `{% block scripts %}`
- Each button has `data-group="fieldname"` and `data-val="1-5"`
- A hidden `<input id="fieldname-val" name="fieldname">` receives the click value
- Pre-fill in edit forms: set initial button colors and hidden input value from the model

### Filter bar
- Items list supports `?status=Active` / `?status=Done` / `?status=Archived`
- Route reads `request.args.get("status")` and applies `.filter_by(status=...)` conditionally
- Template renders buttons as links; active filter highlighted with `bg-indigo-700`

### Helpers (`app/utils/helpers.py`)
- `current_profile()` — returns active profile name
- `_int(value)` — safe int cast, returns `None` on failure
- `_float(value)` — safe float cast, returns `None` on failure

---

## CLI Commands

| Command | Description |
|---|---|
| `flask seed` | Wipe and re-seed 6 example items per profile (destructive) |
| `flask db-backup` | Dump DB to `backups/<name>_<timestamp>.sql` |
| `flask db-restore <file>` | Restore DB from a SQL file |

---

## Routes

| Blueprint | Method | Path | Purpose |
|---|---|---|---|
| main | GET | `/` | Dashboard — stat cards + recent items |
| main | POST | `/switch-profile` | Switch active profile |
| items | GET | `/items/` | Item list (supports `?status=` filter) |
| items | GET/POST | `/items/add` | Add item |
| items | GET/POST | `/items/<id>/edit` | Edit item |
| items | POST | `/items/<id>/delete` | Delete item |

---

## Config Variables

| Variable | Default | Description |
|---|---|---|
| `FLASK_SECRET_KEY` | `change-me` | Session signing key |
| `DATABASE_URL` | — | `mysql+pymysql://user:password@host/dbname` |
| `FLASK_ENV` | `development` | `development` or `production` |
| `APP_NAME` | `My App` | App name in nav and titles |
| `TAILSCALE_IP` | `127.0.0.1` | IP to bind to |
| `PORT` | `5000` | Port to bind to |
| `PROFILES` | `Player 1` | Comma-separated profile names |

---

## Gotchas

- **`db.create_all()` needs models imported first.** The factory handles this at runtime. In a raw shell: `from app import db, models` before `db.create_all()`.
- **Use `python run.py`, not `flask run`** — `flask run` ignores `TAILSCALE_IP`.
- **`flask seed` wipes all data** before re-inserting. Never run against real data.
- **MySQL lock wait timeout** in `flask shell` if a previous session left an open transaction. Exit all shells, wait a moment, retry.
- **SQLite doesn't enforce Enum values** at the DB level — the route validates submitted values against `VALID_STATUSES` instead.

---

## What Not to Do

- Do not expose the app on `0.0.0.0` — Tailscale IP binding only
- Do not commit `.env`
- Do not add user accounts or a login system — Tailscale handles access
- Do not use `flask run` in production — use Gunicorn
- Do not run `flask seed` against a database with real data you want to keep
