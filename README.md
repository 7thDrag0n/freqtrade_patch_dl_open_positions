# freqtrade_patch_dl_open_positions
<p align="center">
<pre>
_________   __  .__    ________                                          
\______  \_/  |_|  |__ \______ \____________     ____   ____   ____      
    /    /\   __\  |  \ |    |  \_  __ \__  \   / ___\ /  _ \ /    \     
   /    /  |  | |   Y  \|    `   \  | \// __ \_/ /_/  >  <_> )   |  \    
  /____/   |__| |___|  /_______  /__|  (____  /\___  / \____/|___|  /    
                     \/        \/           \//_____/             \/     
</pre>
</p>

v1.4

*** 1. Fix for Freqtrade/FreqAI - download data also for opened positions

*** 2. Fix for slow interface advise_exit                                

*** 3. Enrich ROI (needs manual editing for older versions)
<img width="1091" height="296" alt="image" src="https://github.com/user-attachments/assets/03f4b68b-0cee-495b-b946-5aec37b6ad6b" />

v1.5

*** 4. Do not preserve hyperopted epochs trials with 0 trades as consumes the max number of epochs

*** Tested FT versions 2024.5 - 2026.8

#############################################################################################

# freqtrade_patch_ccxt_fetchmarkets

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
    python patch_ccxt_fetchmarkets.py 500          # non-interactive (original defaults were previously 20 or 200)
    python patch_ccxt_fetchmarkets.py --restore    # roll back from .bak files
    python patch_ccxt_fetchmarkets.py --dry-run    # test the patch

Idempotent and re-runnable. Must be run inside the same environment freqtrade uses as it patch ccxt library, so of course need to run it every time you update it.

#############################################################################################

# patch_freqtrade_log_tz.py

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


#############################################################################################
#############################################################################################
For more stuff checkout Alex Crypto King Discord
https://discord.gg/UeshjrAs
https://discord.com/channels/1238181199206154373/1284586552760074323
