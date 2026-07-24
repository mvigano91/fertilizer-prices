# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository overview

This repo contains two independent, unrelated deliverables:

- `tictactoe.html` — a self-contained, static two-player tic-tac-toe game. No build system, package manager, linter, or test suite — the file is meant to be opened directly in a browser.
- `fertilizer_prices/` — a Python app that charts historical commodity prices, centered on fertilizers (Azoto/Fosforo/Potassio) but expanded to related/comparison series (energy incl. natural gas, agriculture, metals, ...), available both as a Tkinter desktop GUI and as a Streamlit web app.

## tictactoe.html

### Running / viewing

Open `tictactoe.html` directly in a browser (double-click, or `start tictactoe.html` on Windows). No server, install step, or build process is involved — all CSS, JS, and fonts are inlined in the one file.

### Architecture

`tictactoe.html` is structured as three inline blocks in a single file:

- **`<style>`**: theming is done entirely through CSS custom properties defined on `:root`. Two fonts (Caveat for display text, JetBrains Mono for UI/score text) are embedded as base64 `data:` URIs via `@font-face` so the page has zero external network dependencies. Light/dark theme values are defined on `:root`, overridden under `@media (prefers-color-scheme: dark)`, and overridden again under `:root[data-theme="dark"]` / `:root[data-theme="light"]` for explicit theme toggles — components should always read theme values through the custom properties, never hardcode colors.
- **Board markup**: the board is built from stacked absolutely-positioned SVG layers (`#gridSvg`, `#markSvg`, `#winSvg`) plus a transparent button grid (`#board`) on top for hit-testing/keyboard access. Grid lines and X/O marks are not static assets — they're generated at runtime as slightly randomized ("hand-drawn") SVG paths using a seeded PRNG (`mulberry32`), then animated on with `stroke-dasharray`/`stroke-dashoffset`.
- **`<script>`**: a single IIFE holding all game state (`board`, `current`, `over`, `score`) and logic (move handling, win/draw detection via `WIN_LINES`, score tracking, round reset). No external libraries or frameworks are used.

When editing this file, keep it a single self-contained HTML document (no external font/script/style requests) — that constraint is intentional so the game works offline and can be shared as one file.

## fertilizer_prices/

A GUI to chart historical commodity prices from two selectable data sources: World Bank "Pink Sheet" (real market prices, all 71 commodities in the file — not just fertilizers, see `DATA_SOURCES_CATALOG.md`) and FRED (a curated set of ~21 PPI/price series: the original fertilizer indices plus natural gas, sulfur, upstream/sector detail, and demand-side agricultural series, also cataloged in `DATA_SOURCES_CATALOG.md`). Both sources are monthly only, so the GUI's granularity options are Mensile/Trimestrale/Annuale (never daily/weekly — there is no free daily source for these products).

### Running / viewing

```
pip install -r fertilizer_prices/requirements.txt
```

- **Desktop (Tkinter)**: `python fertilizer_prices/app.py`
- **Web (Streamlit)**: live at https://fertilizer-prices-1.streamlit.app/ (deployed via Streamlit Community Cloud, auto-redeploys on push to `master`). To run locally: `streamlit run fertilizer_prices/streamlit_app.py`

The FRED data source requires a free `FRED_API_KEY` (https://fred.stlouisfed.org/docs/api/api_key.html):
- Desktop app: read from the `FRED_API_KEY` environment variable.
- Streamlit Cloud deployment: read from Streamlit secrets (App settings → Secrets), falling back to the env var if secrets aren't configured.

### Architecture

- `data.py` — all data loading/normalization logic, UI-framework-agnostic (used unchanged by both GUIs):
  - `load_pink_sheet_prices()` parses the local `data/CMO-Historical-Data-Monthly.xlsx` (World Bank "Monthly Prices" sheet), cached in the module-level `_pink_sheet_cache` (cleared by `refresh_pink_sheet_file()`).
  - `load_fred_series(series_id)` calls the FRED REST API, cached in the module-level `_fred_cache` (`{series_id: pd.Series}`) — a plain in-process dict, not `st.cache_data`, to keep this module framework-agnostic. Lives for the lifetime of the running process only (no manual-refresh button, unlike Pink Sheet); this is intentional — FRED PPI data is monthly, so staleness within a working session is a non-issue, and a restart (dev server relaunch, Streamlit Cloud redeploy/wake) naturally clears it.
  - `get_series(source, product_label, years_back, granularity, mode)` is the single entry point the GUIs call — it resolves the source, clips to the requested years, resamples, and computes period-over-period % change when requested.
  - `get_all_series(source, years_back, granularity, mode)` — same as `get_series` but loops over every label in `SOURCES[source]`, skipping empty results; powers the Streamlit "Statistiche" tab's whole-catalog (WBPS or FRED) mode. Cheap for WBPS (slices from `_pink_sheet_cache`); for FRED it's as many live API calls as there are uncached series, mitigated by `_fred_cache` above.
  - `PINK_SHEET_PRODUCTS` / `FRED_PRODUCTS` / `SOURCES` define the product catalog per source. Labels are prefixed by category (e.g. `"Energia - Gas naturale USA (Henry Hub)"`, `"Domanda - PPI Mais (USA)"`); a trailing `*` on a label (e.g. `"Cereali - Orzo*"`) flags a series that stopped being updated well before the others (discontinued upstream) — keep this suffix in sync across `PINK_SHEET_PRODUCTS`/`FRED_PRODUCTS` and `PRODUCT_INFO` if a series' status changes. See `DATA_SOURCES_CATALOG.md` for the full inventory of what each source offers, what's exposed vs. deliberately left out (duplicates, discontinued series), and how to verify/add a new entry.
  - `PRODUCT_INFO`: label (same key as above) → `(unit, date_range, description)`, shown in the Streamlit sidebar for whichever series (S1..Sn) are currently compiled. `date_range` is a static string, not computed live from the API/file, to avoid re-hitting FRED on every Streamlit rerun — refresh it by hand if it drifts noticeably out of date. Every key in `PINK_SHEET_PRODUCTS`/`FRED_PRODUCTS` must have a matching `PRODUCT_INFO` entry (sanity-check with a one-liner comparing the key sets after editing either).
- `app.py` — Tkinter desktop GUI. **Currently paused**: per explicit user direction, active development happens only on the Streamlit app until the project is further along; `app.py` will be brought back in sync with the Streamlit feature set (multi-series, Pad formulas, regression tab, statistics) in one pass later rather than incrementally. It still supports an optional second overlaid time series (added before the pause) and depends on `matplotlib` directly (`FigureCanvasTkAgg`/`Figure`) — keep `matplotlib` in `requirements.txt` for this reason even though the Streamlit app no longer uses it.
- `streamlit_app.py` — thin orchestrator for the web app: page config, sidebar CSS, wires together the modules below into three tabs:
  - **"Serie storiche"** — the multi-series chart, plus (for the sidebar-selected series) a "Statistiche mobili / volatilità" rolling mean/std section and a "Statistiche descrittive" table. Session state (`chart_error` / `series_result`) is what keeps the last computed result visible across sidebar interactions that aren't "Aggiorna grafico".
  - **"Regressione"** — OLS on the sidebar-selected series' Y/X roles.
  - **"Statistiche"** — fully self-contained, deliberately independent of the sidebar (no `series_result` dependency, doesn't require "Aggiorna grafico"): its own "Anni indietro"/"Granularità" controls, a "Fonte" dropdown (`World Bank Pink Sheet` / `FRED (PPI)`), a "Custom data" button opening an `st.dialog` popup (`_custom_data_dialog()`) with an Excel-filter-style checklist over the combined `series_config.PRODUCT_CATALOG` (search box, per-item checkboxes, a "Seleziona tutto" for the current filter, a right-hand column of current picks each removable via "✕") that takes priority over the Fonte dropdown when non-empty, and a "Calcola" button — nothing is fetched until it's pressed, since a full-FRED or full-catalog fetch can be non-trivially slow. `stats_tab_error`/`stats_tab_result` hold the last computed result with the same sticky session-state pattern as `chart_error`/`series_result`. The custom picker's "confirmed" state lives in `st.session_state["stats_custom_selection"]`; while the dialog is open, in-progress ticks accumulate in `st.session_state["stats_custom_working"]` (a `set`, the actual source of truth for what's checked) rather than trusting individual checkboxes' own persisted state, and each checkbox's displayed value is force-synced from that set on every render — this was a deliberate fix after individual per-widget state proved to not reliably survive being filtered out of view.
- `series_config.py` — sidebar UI and series resolution, shared across tabs so no tab ever re-fetches data another tab already has:
  - `PRODUCT_CATALOG` (module-level, built once by `_build_product_catalog()`): merges `data.PINK_SHEET_PRODUCTS` and `data.FRED_PRODUCTS` into one alphabetically-sorted dict for a single searchable "Prodotto" selectbox — no separate "Fonte dati" selectbox in the sidebar. Combined label = `"<original label> - <WBPS|FRED>"` (`_SOURCE_ABBREV`); the value is `(source, original_label)`, unpacked back into `source`/`product` right after selection so the rest of the pipeline (`validate_years`, `resolve_series`, `data.get_series`) is unaffected by the merge. Also reused by the "Statistiche" tab's custom-ticker picker (see `streamlit_app.py` above).
  - `render_sidebar()` draws the shared controls (years back, granularity) plus a dynamically sized list of series (S1..Sn, add/remove via `st.session_state["num_series"]`), then a per-series info block (unit/date-range/description from `data.PRODUCT_INFO`) and a legend (WBPS/FRED/`*`/PPI meaning) below the "Aggiorna grafico" button.
  - `render_series_controls(label)` draws one series' row: L/R axis (`st.segmented_control`), a "Pad" checkbox that swaps the product/mode controls for a free-text formula (e.g. `S1 - S2`, `S1 * 100`, evaluated with a sandboxed `eval` against the other resolved series), and a "regression role" dropdown (`—`/`Y`/`X1`/`X2`/...) defaulting S1→Y, S2→X1, S3→X2, etc. The "Prodotto" selectbox starts empty (`index=None` + search placeholder) rather than pre-selecting the first option, since `PRODUCT_CATALOG` has ~90 entries and type-to-search is the primary way to pick one.
  - `resolve_series(...)` fetches the non-Pad series via `data.get_series` and resolves Pad formulas (`resolve_pad_formulas`, iterative so a Pad can reference another Pad).
  - `resolve_catalog_labels(years_back, granularity, combined_labels)` — resolves a list of `PRODUCT_CATALOG` combined labels (from the "Statistiche" tab's custom picker) into `{combined_label: pd.Series}` via `data.get_series`, mode fixed to `"Valore assoluto"`. Mirrors `resolve_series`'s error-propagation style (doesn't catch `FredApiKeyMissing`/`FredRequestError`/`ValueError`, leaves that to the caller).
  - `parse_regression_roles(series_result)` reads each series' regression role and returns the chosen Y entry, the ordered X entries, and any validation errors (duplicate Y, duplicate X slot).
- `stats.py` — descriptive/correlation/volatility statistics, pure numpy/pandas, no Streamlit/Plotly imports:
  - `build_aligned_frame(series_by_label)` / `correlation_matrix(frame)` — Pearson correlation across a `{label: pd.Series}` dict, outer-joined (not inner) so `DataFrame.corr()`'s own pairwise-complete NaN handling isn't needlessly shrunk when series have different histories.
  - `rolling_stats(series, window)` — rolling mean/std, feeds the "Statistiche mobili / volatilità" chart.
  - `percentile_of_last(series)` / `zscore_of_last(series)` — where the series' most recent value sits vs. its own full history: percentile (0-100, pandas rank-based, no scipy) and z-score (std-dev units from the mean, unbounded, complements percentile once it saturates at 100).
  - `descriptive_stats(series_result)` vs `descriptive_stats_by_label(series_by_label)` — same output shape (Media/Dev. std/Min/Max/Valore attuale/Percentile attuale/Z-score attuale), but two functions because the two callers pass different input shapes: the former takes the sidebar's list-of-dicts (`series_result`, with `label`/`is_pad`/`formula`/`product`/`source` metadata, indexed by "Serie" with a "Descrizione" column), the latter a plain `{label: pd.Series}` dict (indexed by "Prodotto", no separate description needed since the label already is one).
- `charting.py` — builds all Plotly figures (no statistics here):
  - `build_series_figure(results)` — the multi-series time chart, with a secondary Y axis for series on "R" (Plotly's `make_subplots(secondary_y=True)`, the equivalent of matplotlib's `ax.twinx()`), interactive hover, and `use_container_width=True` sizing.
  - `build_regression_figure(...)` — the "actual vs fitted" scatter for the regression tab: true 1:1 square (equal axis ranges + `scaleanchor`), matching tick density (`dtick`) and grid on both axes, a blue→red recency color gradient, the most recent point highlighted as a green diamond, and the "regression line" drawn as `y = x` (see the in-code comment: for an OLS fit, actual-vs-fitted regressed on itself is algebraically always the y=x diagonal, so no second fit is computed).
  - `build_residuals_figure(...)` — residuals (actual − fitted) over time, bar chart with a zero reference line.
  - `build_correlation_heatmap(corr_df)` — adaptive: annotates each cell with its value for small matrices (≤15 series), drops annotations and shrinks fonts/row-height for larger ones (e.g. the ~71-92-entry WBPS/FRED/custom catalog in the "Statistiche" tab), relying on the color scale + hover for readability at that density.
  - `build_rolling_stats_figure(...)` — a series' own value plus its rolling mean and a shaded ±1 std band.
- `regression.py` — pure numpy/pandas OLS, no Streamlit/Plotly imports: `fit_multilinear_ols(y, x_list)` aligns series on their common dates (inner join + dropna) and solves via `numpy.linalg.lstsq`; `format_equation(...)` renders the fitted equation as text.
- Streamlit's dev-server file watcher only re-executes `streamlit_app.py` itself on save — it does **not** reload already-imported local modules (`series_config`/`stats`/`charting`/`regression`) in a running process. After editing those modules, fully stop and restart the `streamlit run` process (not just save-and-refresh), or edits will silently keep running on stale cached module code.
- `requirements.txt` pins `streamlit>=1.31` (a floor, not an exact version) — the minimum needed for `st.dialog`, used by the "Statistiche" tab's custom-ticker picker popup.
- `data/CMO-Historical-Data-Monthly.xlsx` — local snapshot of the World Bank Pink Sheet. The World Bank's download URL changes periodically (it embeds a report-version hash), so it can't be hardcoded: `data.refresh_pink_sheet_file()` scrapes https://www.worldbank.org/en/research/commodity-markets for the current link, downloads it, overwrites this file, and clears `data.py`'s in-memory cache. Exposed in the Streamlit sidebar as the "Aggiorna dati World Bank" button (`series_config.py`). Since this file is committed to the repo, refreshing it locally leaves the change uncommitted — see the git workflow note below.

## Git workflow

This repo has no CI or deploy step, but the user works on it from more than one computer, so the git workflow exists purely so work is never lost or diverges between machines. As you make changes:

- Run `git pull` at the start of a session, before making any changes, so you're working on top of the latest commits from any other machine.
- If `data/CMO-Historical-Data-Monthly.xlsx` shows as modified (e.g. after clicking "Aggiorna dati World Bank" in the Streamlit sidebar), commit and push it like any other change — otherwise the refreshed data stays stuck on this machine and the other one keeps using stale prices.
- Commit after each meaningful, working change — don't let uncommitted work pile up across sessions.
- Write clean, specific commit messages describing what changed and why (not "update" or "wip").
- Push to the `origin` remote after committing, so history is backed up off this machine and available to the other one.
- Never use `git push --force`, `git reset --hard`, or rewrite published history without explicit confirmation.
- When the user writes "buonanotte", that signals the end of the session: commit any outstanding work (with a clean, specific message) and push to `origin` before ending, so nothing is left uncommitted between sessions.

The `origin` remote is configured at https://github.com/mvigano91/fertilizer-prices.git.
