# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository overview

This repo currently contains a single deliverable: `tictactoe.html`, a self-contained, static two-player tic-tac-toe game. There is no build system, package manager, linter, or test suite — the file is meant to be opened directly in a browser.

## Running / viewing

Open `tictactoe.html` directly in a browser (double-click, or `start tictactoe.html` on Windows). No server, install step, or build process is involved — all CSS, JS, and fonts are inlined in the one file.

## Architecture

`tictactoe.html` is structured as three inline blocks in a single file:

- **`<style>`**: theming is done entirely through CSS custom properties defined on `:root`. Two fonts (Caveat for display text, JetBrains Mono for UI/score text) are embedded as base64 `data:` URIs via `@font-face` so the page has zero external network dependencies. Light/dark theme values are defined on `:root`, overridden under `@media (prefers-color-scheme: dark)`, and overridden again under `:root[data-theme="dark"]` / `:root[data-theme="light"]` for explicit theme toggles — components should always read theme values through the custom properties, never hardcode colors.
- **Board markup**: the board is built from stacked absolutely-positioned SVG layers (`#gridSvg`, `#markSvg`, `#winSvg`) plus a transparent button grid (`#board`) on top for hit-testing/keyboard access. Grid lines and X/O marks are not static assets — they're generated at runtime as slightly randomized ("hand-drawn") SVG paths using a seeded PRNG (`mulberry32`), then animated on with `stroke-dasharray`/`stroke-dashoffset`.
- **`<script>`**: a single IIFE holding all game state (`board`, `current`, `over`, `score`) and logic (move handling, win/draw detection via `WIN_LINES`, score tracking, round reset). No external libraries or frameworks are used.

When editing this file, keep it a single self-contained HTML document (no external font/script/style requests) — that constraint is intentional so the game works offline and can be shared as one file.

## Git workflow

This repo has no CI or deploy step, but the user works on it from more than one computer, so the git workflow exists purely so work is never lost or diverges between machines. As you make changes:

- Run `git pull` at the start of a session, before making any changes, so you're working on top of the latest commits from any other machine.
- Commit after each meaningful, working change — don't let uncommitted work pile up across sessions.
- Write clean, specific commit messages describing what changed and why (not "update" or "wip").
- Push to the `origin` remote after committing, so history is backed up off this machine and available to the other one.
- Never use `git push --force`, `git reset --hard`, or rewrite published history without explicit confirmation.
- When the user writes "buonanotte", that signals the end of the session: commit any outstanding work (with a clean, specific message) and push to `origin` before ending, so nothing is left uncommitted between sessions.

The `origin` remote is configured at https://github.com/mvigano91/fertilizer-prices.git.
