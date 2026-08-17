#!/usr/bin/env python3
"""
Patch ccxt's bybit.fetch_leverage_tiers() pagination cap.

Background
----------
Bybit's /v5/market/risk-limit endpoint is cursor-paginated. ccxt calls it via:

    data = self.get_leverage_tiers_paginated(
        symbol, self.extend({'paginate': True, 'paginationCalls': 50}, params))

'paginationCalls' is hardcoded and acts as a hard stop in fetch_paginated_call_cursor
(`while i < maxCalls`). Once Bybit lists more linear symbols than that budget covers,
the tail of the symbol list is silently dropped -- no error, no warning. Freqtrade then
caches the truncated result for 24h in
    <datadir>/futures/leverage_tiers_<STAKE>.json
which yields max_leverage == 1.0 and
    InvalidOrderException: Maintenance margin rate for XRP/USDT:USDT is unavailable
for the missing pairs.

Raising the cap costs nothing: the loop still exits early on an exhausted cursor or an
empty page, so it performs only as many requests as actually needed.

Usage
-----
    python patch_ccxt_fetchmarkets.py              # prompts, defaults to 500 after 10s
    python patch_ccxt_fetchmarkets.py 500          # non-interactive
    python patch_ccxt_fetchmarkets.py --restore    # roll back from .bak files
    python patch_ccxt_fetchmarkets.py --dry-run

Idempotent and re-runnable. Must be run inside the same environment freqtrade uses.
"""

from __future__ import annotations

import argparse
import py_compile
import re
import shutil
import sys
import threading
from pathlib import Path

DEFAULT_VALUE = 500
INPUT_TIMEOUT = 10

# Deliberately loose so it survives upstream reformatting: we anchor on the call name
# and on the 'paginationCalls' key appearing later on the SAME line, then rewrite only
# the integer. Tolerates single/double quotes, extra whitespace, and `await`.
PATTERN = re.compile(
    r"(get_leverage_tiers_paginated\s*\(.*?['\"]paginationCalls['\"]\s*:\s*)(\d+)"
)


def find_ccxt_root() -> Path:
    try:
        import ccxt
    except ImportError:
        sys.exit("ERROR: ccxt is not importable in this interpreter. "
                 "Activate the freqtrade venv / exec into the container first.")
    root = Path(ccxt.__file__).resolve().parent
    print(f"ccxt {getattr(ccxt, '__version__', '?')} at {root}")
    return root


def find_targets(root: Path) -> list[Path]:
    """All bybit.py variants (sync, async_support, and any future layout)."""
    return sorted(p for p in root.rglob("bybit.py") if p.is_file())


def read_timeout_int(prompt: str, default: int, timeout: int) -> int:
    """input() with a timeout; falls back to `default`. Works on Windows and POSIX."""
    if not sys.stdin or not sys.stdin.isatty():
        print(f"{prompt}(non-interactive stdin, using {default})")
        return default

    box: list[str] = []

    def _read() -> None:
        try:
            box.append(input())
        except (EOFError, KeyboardInterrupt):
            pass

    t = threading.Thread(target=_read, daemon=True)
    print(prompt, end="", flush=True)
    t.start()
    t.join(timeout)

    if not box:
        print(f"\n-> timeout after {timeout}s, using default {default}")
        return default

    raw = box[0].strip()
    if not raw:
        print(f"-> empty input, using default {default}")
        return default
    try:
        val = int(raw)
    except ValueError:
        print(f"-> '{raw}' is not an integer, using default {default}")
        return default
    if val < 1:
        print(f"-> {val} is out of range, using default {default}")
        return default
    return val


def patch_file(path: Path, value: int, dry_run: bool) -> str:
    original = path.read_text(encoding="utf-8")
    found: list[str] = []

    def _sub(m: re.Match) -> str:
        found.append(m.group(2))
        return f"{m.group(1)}{value}"

    patched = PATTERN.sub(_sub, original)

    if not found:
        return "no match"
    if patched == original:
        return f"already {value} ({len(found)} site(s))"
    if dry_run:
        return f"would patch {found} -> {value}"

    backup = path.with_suffix(path.suffix + ".bak")
    if not backup.exists():
        shutil.copy2(path, backup)

    path.write_text(patched, encoding="utf-8")

    try:
        py_compile.compile(str(path), doraise=True, quiet=1)
    except py_compile.PyCompileError as exc:
        shutil.copy2(backup, path)
        return f"SYNTAX ERROR, rolled back: {exc}"

    return f"patched {found} -> {value} (backup: {backup.name})"


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
    ap.add_argument("value", nargs="?", type=int,
                    help=f"paginationCalls value (default {DEFAULT_VALUE})")
    ap.add_argument("--dry-run", action="store_true", help="report only, change nothing")
    ap.add_argument("--restore", action="store_true", help="restore from .bak files")
    args = ap.parse_args()

    root = find_ccxt_root()
    targets = find_targets(root)
    if not targets:
        sys.exit("ERROR: no bybit.py found under the ccxt package.")

    if args.restore:
        print("Restoring:")
        restore(targets)
        return 0

    if args.value is not None:
        value = args.value
    else:
        value = read_timeout_int(
            f"paginationCalls [{DEFAULT_VALUE}] ({INPUT_TIMEOUT}s): ",
            DEFAULT_VALUE, INPUT_TIMEOUT)

    print(f"\nTarget value: {value}\n")
    touched = 0
    for path in targets:
        result = patch_file(path, value, args.dry_run)
        if result == "no match":
            continue
        touched += 1
        print(f"  {path}\n    {result}")

    if touched == 0:
        print("  No call site matched. Upstream may have restructured "
              "fetch_leverage_tiers(); inspect bybit.py manually for "
              "'get_leverage_tiers_paginated'.")
        return 1

    if not args.dry_run:
        print("\nDone. Now delete the stale freqtrade cache so the tiers are refetched:")
        print("  rm <datadir>/futures/leverage_tiers_USDT.json")
        print("  (typically user_data/data/bybit/futures/leverage_tiers_USDT.json)")
        print("\nVerify:")
        print("  python -c \"import ccxt; e=ccxt.bybit({'options':{'defaultType':'swap'}});"
              " e.load_markets(); t=e.fetch_leverage_tiers();"
              " print(len(t), 'XRP/USDT:USDT' in t)\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
