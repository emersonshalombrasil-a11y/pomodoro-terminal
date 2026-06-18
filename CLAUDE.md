# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A single-file terminal Pomodoro timer (`pomodoro.py`) using [`rich`](https://github.com/Textualize/rich) for TUI rendering. Notifications use macOS `osascript` — non-macOS platforms will silently skip them. Python 3.10+ is required.

## Setup & Running

```bash
pip install -r requirements.txt
python pomodoro.py
```

No build step, no test suite, no linter configuration exists in the repo.

## Architecture

The entire application lives in `pomodoro.py`. Key sections:

**Keyboard input** — `_read_keys()` runs as a daemon thread, putting raw characters into the global `_key_pressed` (protected by `_key_lock`). `get_key()` consumes and clears it each tick. This avoids blocking the render loop. The thread sets the terminal to raw mode (`tty.setraw`) and restores it via `termios` on exit.

**Render loop** — `run_phase(phase, minutes, ...)` owns a `rich.live.Live` context and loops at ~20 fps (`time.sleep(0.05)`), calling `build_layout()` each iteration to reconstruct the full `Layout`. `build_layout()` calls `today_stats()` → `load_history()` on every frame, reading `~/.pomodoro_history.json` from disk each time.

**Phase sequencing** — `main()` drives the cycle: work → short break (×`LONG_BREAK_EVERY`) → long break → repeat. `run_phase` returns `(completed: bool, quit: bool)` to signal whether the phase finished naturally, was skipped (`s`), or the user quit (`q`).

**Persistence** — history is stored in `~/.pomodoro_history.json` as `{ "YYYY-MM-DD": [{ "type", "duration", "at" }] }`. Only completed phases are saved (saves happen after `completed == True`).

## Configuration

All timing constants are at the top of `pomodoro.py`:

```python
WORK_MINS = 25
SHORT_BREAK_MINS = 5
LONG_BREAK_MINS = 15
LONG_BREAK_EVERY = 4
HISTORY_FILE = Path.home() / ".pomodoro_history.json"
```

## Phase identifiers

The string keys `"work"`, `"short"`, and `"long"` are used across `phase_color()`, `phase_label()`, `run_phase()`, and `save_session()`. Any new phase must be added to all four places.
