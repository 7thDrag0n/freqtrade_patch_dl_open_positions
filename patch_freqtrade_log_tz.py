#!/usr/bin/env python3
"""
Patch freqtrade's RPC log endpoint to report log timestamps in local time
instead of UTC.

Background
----------
`RPC._rpc_get_logs()` (freqtrade/rpc/rpc.py) is what feeds FreqUI's Logs tab
and the `/api/v1/logs` endpoint. It builds each row as:

    format_date(dt_from_ts(r.created))

`dt_from_ts()` (freqtrade/util/datetime_helpers.py) is hardcoded to
    datetime.fromtimestamp(timestamp, tz=UTC)
so the UI's log timestamps are always UTC, no matter what `TZ` the
container/host is set to.

This is a regression introduced in commit ec5dede4 ("chore: use timezone
aware datetime objects", 2026-08-03). Before that commit the line read:

    format_date(datetime.fromtimestamp(r.created))

which used the local timezone -- and matches what the plain-text file/console
logger still does today (it was not touched by that commit, so file logs and
the UI now disagree). This script reverts just that one call site back to
local time.

It does NOT touch the other two `dt_from_ts()` call sites in rpc.py (trade
open-timestamp humanizing, backtest start_date default) -- those are
legitimately timezone-aware and out of scope.

Why this approach survives upstream changes
--------------------------------------------
The anchor is `dt_from_ts(r.created)` -- the combination of that helper name
and the logging record's `.created` attribute is unlikely to be renamed
(`r.created` is a stable Python `logging.LogRecord` attribute, and this is
the only place in rpc.py that calls `dt_from_ts` on it). The regex tolerates
reformatting (whitespace, line breaks, `record` instead of `r`, `await`,
etc.) around that call, the same way the ccxt pagination patch tolerates
reformatting around `paginationCalls`.

If upstream ever removes the plain `datetime` class from rpc.py's imports
(unlikely -- it's used throughout the file already), this script adds it
back automatically.

Usage
-----
    python patch_freqtrade_log_tz.py              # patch
    python patch_freqtrade_log_tz.py --restore     # roll back from .bak
    python patch_freqtrade_log_tz.py --dry-run     # report only

Idempotent and re-runnable. Must be run inside the same environment/container
freqtrade runs in (so `import freqtrade` resolves to the live install), and
freqtrade must be restarted afterwards for the change to take effect.
"""

from __future__ import annotations

import argparse
import py_compile
import re
import shutil
import sys
from pathlib import Path

# Anchor: dt_from_ts(<record var>.created), tolerant of the record variable's
# name and of whitespace/line-break reformatting around the call.
PATTERN = re.compile(r"dt_from_ts\s*\(\s*(\w+)\.created\s*\)")

REPLACEMENT_TEMPLATE = "datetime.fromtimestamp({var}.created)"

# Matches a `datetime` class import, e.g.:
#   from datetime import datetime
#   from datetime import UTC, date, datetime, timedelta
DATETIME_IMPORT_RE = re.compile(r"^from datetime import\b.*\bdatetime\b", re.MULTILINE)
ANY_FROM_DATETIME_IMPORT_RE = re.compile(r"^from datetime import\b.*$", re.MULTILINE)


def find_freqtrade_root() -> Path:
    try:
        import freqtrade
    except ImportError:
        sys.exit(
            "ERROR: freqtrade is not importable in this interpreter. "
            "Activate the freqtrade venv / exec into the container first."
        )
    root = Path(freqtrade.__file__).resolve().parent
    print(f"freqtrade {getattr(freqtrade, '__version__', '?')} at {root}")
    return root


def find_targets(root: Path) -> list[Path]:
    """rpc/rpc.py under the freqtrade package (normally exactly one)."""
    return sorted(
        p for p in root.rglob("rpc.py") if p.is_file() and p.parent.name == "rpc"
    )


def ensure_datetime_import(content: str) -> tuple[str, bool]:
    """Make sure the plain `datetime` class is importable in this module.
    Returns (possibly-modified content, whether it changed)."""
    if DATETIME_IMPORT_RE.search(content):
        return content, False

    m = ANY_FROM_DATETIME_IMPORT_RE.search(content)
    if m:
        line = m.group(0)
        if "datetime" not in line:
            new_line = line.rstrip() + ", datetime"
            return content.replace(line, new_line, 1), True
        return content, False

    # No `from datetime import ...` line at all: add one near the top.
    return "from datetime import datetime\n" + content, True


def patch_file(path: Path, dry_run: bool) -> str:
    original = path.read_text(encoding="utf-8")
    matches = PATTERN.findall(original)

    if not matches:
        return "no match"

    def _sub(m: re.Match) -> str:
        var = m.group(1)
        return REPLACEMENT_TEMPLATE.format(var=var)

    patched = PATTERN.sub(_sub, original)

    if patched == original:
        return f"already patched ({len(matches)} site(s))"

    patched, import_added = ensure_datetime_import(patched)

    if dry_run:
        note = " (+ would add `datetime` import)" if import_added else ""
        return f"would patch {matches} -> datetime.fromtimestamp(...){note}"

    backup = path.with_suffix(path.suffix + ".bak")
    if not backup.exists():
        shutil.copy2(path, backup)

    path.write_text(patched, encoding="utf-8")

    try:
        py_compile.compile(str(path), doraise=True, quiet=1)
    except py_compile.PyCompileError as exc:
        shutil.copy2(backup, path)
        return f"SYNTAX ERROR, rolled back: {exc}"

    note = " (+ added `datetime` import)" if import_added else ""
    return f"patched {matches} -> datetime.fromtimestamp(...) (backup: {backup.name}){note}"


def restore(targets: list[Path]) -> None:
    n = 0
    for path in targets:
        backup = path.with_suffix(path.suffix + ".bak")
        if backup.exists():
            shutil.copy2(backup, path)
            print(f"  restored {path}")
            n += 1
    if n == 0:
        print("  nothing to restore (no .bak files found)")


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--dry-run", action="store_true", help="report only, change nothing")
    ap.add_argument("--restore", action="store_true", help="restore from .bak files")
    args = ap.parse_args()

    root = find_freqtrade_root()
    targets = find_targets(root)
    if not targets:
        sys.exit("ERROR: no rpc/rpc.py found under the freqtrade package.")

    if args.restore:
        print("Restoring:")
        restore(targets)
        return 0

    print()
    touched = 0
    for path in targets:
        result = patch_file(path, args.dry_run)
        if result == "no match":
            continue
        touched += 1
        print(f"  {path}\n    {result}")

    if touched == 0:
        print(
            "  No call site matched. Upstream may have restructured "
            "_rpc_get_logs() (e.g. renamed dt_from_ts or the record "
            "variable); inspect rpc/rpc.py manually for the log-row "
            "construction (search for 'r.created' or 'bufferHandler')."
        )
        return 1

    if not args.dry_run:
        print(
            "\nDone. Restart freqtrade (recreate the container / restart the "
            "process) so the change takes effect -- a plain `docker restart` "
            "is enough, no rebuild needed since this patches the installed "
            "package in place.\n"
            "Note: this patch lives inside the container's site-packages, so "
            "it will be wiped out by the next `docker compose pull` / image "
            "update. Re-run this script after any freqtrade upgrade."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
