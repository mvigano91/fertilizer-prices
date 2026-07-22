# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository overview

This repo contains two independent, unrelated deliverables:

- `tictactoe.html` — a self-contained, static two-player tic-tac-toe game. No build system, package manager, linter, or test suite — the file is meant to be opened directly in a browser.
- `fertilizer_prices/` — a Python app that charts historical fertilizer prices (Azoto/Fosforo/Potassio), available both as a Tkinter desktop GUI and as a Streamlit web app.

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

A GUI to chart the historical price of nitrogen/phosphorus/potassium fertilizers (Urea, DAP, TSP, Phosphate rock, Potassium chloride), from two selectable data sources: World Bank "Pink Sheet" (real market prices, $/mt) and FRED (US PPI indices). Both sources are monthly only, so the GUI's granularity options are Mensile/Trimestrale/Annuale (never daily/weekly — there is no free daily source for these products).

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
  - `load_pink_sheet_prices()` parses the local `data/CMO-Historical-Data-Monthly.xlsx` (World Bank "Monthly Prices" sheet).
  - `load_fred_series()` calls the FRED REST API.
  - `get_series(source, product_label, years_back, granularity, mode)` is the single entry point the GUIs call — it resolves the source, clips to the requested years, resamples, and computes period-over-period % change when requested.
  - `PINK_SHEET_PRODUCTS` / `FRED_PRODUCTS` / `SOURCES` define the product catalog per source, used to populate the product dropdown dynamically based on the chosen source.
- `app.py` — Tkinter desktop GUI. **Currently paused**: per explicit user direction, active development happens only on the Streamlit app until the project is further along; `app.py` will be brought back in sync with the Streamlit feature set (multi-series, Pad formulas, regression tab) in one pass later rather than incrementally. It still supports an optional second overlaid time series (added before the pause) and depends on `matplotlib` directly (`FigureCanvasTkAgg`/`Figure`) — keep `matplotlib` in `requirements.txt` for this reason even though the Streamlit app no longer uses it.
- `streamlit_app.py` — thin orchestrator for the web app: page config, sidebar CSS, wires together the modules below into two tabs, "Serie storiche" and "Regressione". Session state (`chart_error` / `series_result`) is what keeps the last computed result visible across sidebar interactions that aren't "Aggiorna grafico".
- `series_config.py` — sidebar UI and series resolution, shared by both tabs so the regression tab never re-fetches data:
  - `render_sidebar()` draws the shared controls (years back, granularity) plus a dynamically sized list of series (S1..Sn, add/remove via `st.session_state["num_series"]`).
  - `render_series_controls(label)` draws one series' row: L/R axis (`st.segmented_control`), a "Pad" checkbox that swaps the source/product/mode controls for a free-text formula (e.g. `S1 - S2`, `S1 * 100`, evaluated with a sandboxed `eval` against the other resolved series), and a "regression role" dropdown (`—`/`Y`/`X1`/`X2`/...) defaulting S1→Y, S2→X1, S3→X2, etc.
  - `resolve_series(...)` fetches the non-Pad series via `data.get_series` and resolves Pad formulas (`resolve_pad_formulas`, iterative so a Pad can reference another Pad).
  - `parse_regression_roles(series_result)` reads each series' regression role and returns the chosen Y entry, the ordered X entries, and any validation errors (duplicate Y, duplicate X slot).
- `charting.py` — builds all Plotly figures (no statistics here):
  - `build_series_figure(results)` — the multi-series time chart, with a secondary Y axis for series on "R" (Plotly's `make_subplots(secondary_y=True)`, the equivalent of matplotlib's `ax.twinx()`), interactive hover, and `use_container_width=True` sizing.
  - `build_regression_figure(...)` — the "actual vs fitted" scatter for the regression tab: true 1:1 square (equal axis ranges + `scaleanchor`), matching tick density (`dtick`) and grid on both axes, a blue→red recency color gradient, the most recent point highlighted as a green diamond, and the "regression line" drawn as `y = x` (see the in-code comment: for an OLS fit, actual-vs-fitted regressed on itself is algebraically always the y=x diagonal, so no second fit is computed).
  - `build_residuals_figure(...)` — residuals (actual − fitted) over time, bar chart with a zero reference line.
- `regression.py` — pure numpy/pandas OLS, no Streamlit/Plotly imports: `fit_multilinear_ols(y, x_list)` aligns series on their common dates (inner join + dropna) and solves via `numpy.linalg.lstsq`; `format_equation(...)` renders the fitted equation as text.
- Streamlit's dev-server file watcher only re-executes `streamlit_app.py` itself on save — it does **not** reload already-imported local modules (`series_config`/`charting`/`regression`) in a running process. After editing those modules, fully stop and restart the `streamlit run` process (not just save-and-refresh), or edits will silently keep running on stale cached module code.
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
