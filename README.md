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

######################################################################################################

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
    python patch_ccxt_fetchmarkets.py 500          # non-interactive
    python patch_ccxt_fetchmarkets.py --restore    # roll back from .bak files
    python patch_ccxt_fetchmarkets.py --dry-run

Idempotent and re-runnable. Must be run inside the same environment freqtrade uses.

######################################################################################################
For more stuff checkout Alex Crypto King Discord
https://discord.gg/UeshjrAs
https://discord.com/channels/1238181199206154373/1284586552760074323
