# PATTERNS.md — Quick-reference cheat sheet

Jump to any pattern in this codebase. Each section shows exactly which files to edit and what to copy.

---

## Star rating widget

**Where:** `app/templates/items/add.html` (add), `app/templates/items/edit.html` (pre-filled edit), `app/templates/base.html` (JS handler)

**Model field:**
```python
# models.py
priority = db.Column(db.Integer, nullable=True)  # 1–5; None = not rated
```

**Form (add — no initial value):**
```html
<div class="flex gap-1">
  {% for i in range(1, 6) %}
  <button type="button"
          class="star-btn text-2xl text-gray-600 hover:text-yellow-400 transition-colors leading-none"
          data-group="priority" data-val="{{ i }}">★</button>
  {% endfor %}
</div>
<input type="hidden" id="priority-val" name="priority" value="">
```

**Form (edit — pre-filled):**
```html
{% set current_priority = item.priority or 0 %}
{% for i in range(1, 6) %}
<button type="button"
        class="star-btn text-2xl {{ 'text-yellow-400' if i <= current_priority else 'text-gray-600' }} hover:text-yellow-400 transition-colors leading-none"
        data-group="priority" data-val="{{ i }}">★</button>
{% endfor %}
<input type="hidden" id="priority-val" name="priority" value="{{ item.priority or '' }}">
```

**Display (inline):**
```html
{% for i in range(1, 6) %}
  <span class="{{ 'text-yellow-400' if item.priority and i <= item.priority else 'text-gray-700' }}">★</span>
{% endfor %}
```

**Display (macro):**
```html
{% from "macros.html" import stars %}
{{ stars(item.priority) }}  {# handles None gracefully #}
```

**Route (read the submitted value):**
```python
from app.utils.helpers import _int
priority = _int(request.form.get("priority", ""))  # None if blank or not clicked
```

---

## Status badge (enum field)

**Where:** `app/models.py` (field), `app/templates/items/index.html` (badge), `app/templates/main/index.html` (badge), `app/blueprints/items.py` (validation)

**Model field:**
```python
# models.py
status = db.Column(
    db.Enum("Active", "Done", "Archived", name="itemstatus"),
    nullable=False,
    default="Active",
)
```

**Badge in template:**
```html
{% if item.status == "Active" %}
  <span class="text-xs px-2 py-0.5 rounded-full bg-green-900 text-green-300">Active</span>
{% elif item.status == "Done" %}
  <span class="text-xs px-2 py-0.5 rounded-full bg-blue-900 text-blue-300">Done</span>
{% else %}
  <span class="text-xs px-2 py-0.5 rounded-full bg-gray-700 text-gray-400">Archived</span>
{% endif %}
```

**Select in form (add):**
```html
<select name="status">
  <option value="Active" selected>Active</option>
  <option value="Done">Done</option>
  <option value="Archived">Archived</option>
</select>
```

**Select in form (edit — pre-selected):**
```html
{% for s in ["Active", "Done", "Archived"] %}
<option value="{{ s }}" {{ 'selected' if item.status == s else '' }}>{{ s }}</option>
{% endfor %}
```

**Route validation:**
```python
VALID_STATUSES = ("Active", "Done", "Archived")
status = request.form.get("status", "Active").strip()
if status not in VALID_STATUSES:
    status = "Active"
```

**To add a new status value:** update the `Enum()` in `models.py`, add an `elif` branch in each template that renders the badge, add the option to form selects, add to `VALID_STATUSES` in `items.py`, and run a DB migration.

---

## Filter bar (query-param filtering)

**Where:** `app/blueprints/items.py` (route), `app/templates/items/index.html` (buttons)

**Route:**
```python
@items_bp.route("/")
def index():
    profile = current_profile()
    status_filter = request.args.get("status", "").strip()
    query = Item.query.filter_by(profile_id=profile)
    if status_filter in ("Active", "Done", "Archived"):
        query = query.filter_by(status=status_filter)
    items = query.order_by(Item.updated_at.desc()).all()
    return render_template("items/index.html", items=items, status_filter=status_filter)
```

**Filter buttons in template:**
```html
<a href="{{ url_for('items.index') }}"
   class="{{ 'bg-indigo-700 text-white' if not status_filter else 'bg-gray-800 text-gray-400 hover:text-white' }} px-3 py-1.5 rounded text-sm">
  All
</a>
{% for label in ["Active", "Done", "Archived"] %}
<a href="{{ url_for('items.index', status=label) }}"
   class="{{ 'bg-indigo-700 text-white' if status_filter == label else 'bg-gray-800 text-gray-400 hover:text-white' }} px-3 py-1.5 rounded text-sm">
  {{ label }}
</a>
{% endfor %}
```

---

## Flash messages

**Where:** `app/templates/base.html` (rendering), any blueprint route (sending)

**Send from a route:**
```python
flash("Item added successfully.", "success")  # green banner
flash("Name is required.",        "error")    # red banner
```

**The rendering loop in `base.html` already handles display** — no template changes needed.

---

## Profile scoping

**These 3 lines are required in every route that reads or writes data:**

```python
from app.utils.helpers import current_profile

profile = current_profile()                                          # 1. get active profile
items   = Item.query.filter_by(profile_id=profile).all()            # 2. scope the query
item    = Item.query.filter_by(id=item_id, profile_id=profile).first_or_404()  # 3. scope single fetch
```

**On write:**
```python
item = Item(profile_id=profile, name=name, ...)
```

**Context processor** in `app/__init__.py` injects `current_profile` (str) and `profiles` (list) into every template automatically — no need to pass them manually from routes.

---

## CRUD blueprint (step-by-step to add a new feature)

1. **Create** `app/blueprints/myfeature.py` — copy `items.py`, rename `items_bp` → `myfeature_bp`, swap `Item` for your model.

2. **Register** in `app/__init__.py`:
   ```python
   from app.blueprints.myfeature import myfeature_bp
   app.register_blueprint(myfeature_bp, url_prefix="/myfeature")
   ```

3. **Add a nav link** in `app/templates/base.html`:
   ```html
   <a href="{{ url_for('myfeature.index') }}"
      class="text-sm {{ 'text-white font-medium' if request.path.startswith('/myfeature') else 'text-gray-400 hover:text-white' }}">
     My Feature
   </a>
   ```

4. **Create templates** in `app/templates/myfeature/` — copy from `app/templates/items/`.

5. **Add the model** to `app/models.py` — copy the `Item` class, rename it, adjust fields.

---

## Form field patterns

| Field type | HTML element | Notes |
|---|---|---|
| Required text | `<input type="text" required>` | Add `autofocus` on the first field |
| Optional text | `<input type="text">` | Route: `or None` to store null when blank |
| Textarea | `<textarea rows="3">{{ value or '' }}</textarea>` | Value goes between tags, not in `value=` |
| Select / enum | `<select>` + `<option selected>` | Pre-select with `{{ 'selected' if item.x == s }}` |
| Star rating | `.star-btn` buttons + hidden input | See star rating section above |
| Checkbox | `<input type="checkbox" name="x" value="1">` | Route: `bool(request.form.get("x"))` |

**Consistent input class:**
```
bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100
focus:outline-none focus:border-indigo-500 transition-colors
```

---

## Stat cards

**Where:** `app/blueprints/main.py` (queries), `app/templates/main/index.html` (cards)

**Route — add a query per card:**
```python
item_count   = Item.query.filter_by(profile_id=profile).count()
active_count = Item.query.filter_by(profile_id=profile, status="Active").count()
```

**Template card:**
```html
<div class="bg-gray-900 rounded-xl p-5 flex flex-col gap-1">
  <span class="text-3xl font-bold text-green-400">{{ active_count }}</span>
  <span class="text-sm text-gray-500">Active</span>
</div>
```

**Color convention:** gray = total/neutral, green = active/positive, blue = done/complete, red = errors/blocked, yellow = pending/warning.
