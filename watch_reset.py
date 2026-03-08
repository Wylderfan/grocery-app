#!/usr/bin/env python3
"""
Watch app/ for Python file changes, then automatically drop, recreate,
and reseed the database via `flask db-reset --yes`.

Usage:
    python watch_reset.py           # watches app/ (all .py files)
    python watch_reset.py models.py # watches a single file

Press Ctrl+C to stop.
"""
import os
import subprocess
import sys
import time

WATCH_DIR     = "app"
POLL_INTERVAL = 1.0  # seconds between checks


def _mtimes(path):
    """Return {filepath: mtime} for every .py file under path."""
    result = {}
    if os.path.isfile(path):
        result[path] = os.stat(path).st_mtime
        return result
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith(".py"):
                full = os.path.join(root, f)
                try:
                    result[full] = os.stat(full).st_mtime
                except OSError:
                    pass
    return result


def _reset():
    print("\n--- change detected — running flask db-reset ---")
    result = subprocess.run(["flask", "db-reset", "--yes"])
    if result.returncode == 0:
        print("--- reset complete ---\n")
    else:
        print("--- reset FAILED (see output above) ---\n")


def main():
    watch_target = sys.argv[1] if len(sys.argv) > 1 else WATCH_DIR
    if not os.path.exists(watch_target):
        print(f"Error: '{watch_target}' does not exist.", file=sys.stderr)
        sys.exit(1)

    print(f"Watching {watch_target!r} for Python changes. Ctrl+C to stop.\n")

    last = _mtimes(watch_target)

    while True:
        time.sleep(POLL_INTERVAL)
        current = _mtimes(watch_target)

        changed_files = [
            path for path, mtime in current.items()
            if last.get(path) != mtime
        ]

        if changed_files:
            for f in changed_files:
                print(f"  modified: {f}")
            _reset()
            last = _mtimes(watch_target)
        else:
            last = current


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(0)
