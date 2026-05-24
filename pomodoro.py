#!/usr/bin/env python3
import json
import os
import sys
import time
import subprocess
import threading
import termios
import tty
from datetime import date, datetime
from pathlib import Path

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.table import Table
from rich.text import Text
from rich.align import Align

# ── Config ──────────────────────────────────────────────────────────────
WORK_MINS = 25
SHORT_BREAK_MINS = 5
LONG_BREAK_MINS = 15
LONG_BREAK_EVERY = 4
HISTORY_FILE = Path.home() / ".pomodoro_history.json"

console = Console()

# ── History ──────────────────────────────────────────────────────────────
def load_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return {}

def save_session(session_type: str, duration_secs: int):
    history = load_history()
    today = str(date.today())
    if today not in history:
        history[today] = []
    history[today].append({
        "type": session_type,
        "duration": duration_secs,
        "at": datetime.now().strftime("%H:%M"),
    })
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def today_stats():
    history = load_history()
    today = str(date.today())
    sessions = history.get(today, [])
    pomodoros = [s for s in sessions if s["type"] == "work"]
    total_focus = sum(s["duration"] for s in pomodoros)
    return len(pomodoros), total_focus

# ── Notification ─────────────────────────────────────────────────────────
def notify(title: str, message: str):
    try:
        script = f'display notification "{message}" with title "{title}" sound name "Glass"'
        subprocess.run(["osascript", "-e", script], check=False, capture_output=True)
    except Exception:
        pass

# ── Keyboard input (non-blocking) ────────────────────────────────────────
_key_pressed = None
_key_lock = threading.Lock()

def _read_keys():
    global _key_pressed
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            with _key_lock:
                _key_pressed = ch
            if ch in ("q", "Q"):
                break
    except Exception:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

def get_key():
    global _key_pressed
    with _key_lock:
        k = _key_pressed
        _key_pressed = None
    return k

# ── UI helpers ───────────────────────────────────────────────────────────
TOMATO = "🍅"
BREAK_ICON = "☕"
PAUSE_ICON = "⏸ "
PLAY_ICON  = "▶ "

def phase_color(phase: str) -> str:
    return {"work": "red", "short": "green", "long": "cyan"}[phase]

def phase_label(phase: str) -> str:
    return {"work": "FOCO", "short": "PAUSA CURTA", "long": "PAUSA LONGA"}[phase]

def format_time(secs: int) -> str:
    m, s = divmod(max(secs, 0), 60)
    return f"{m:02d}:{s:02d}"

def build_layout(phase, remaining, total, paused, pomo_count, cycle):
    color = phase_color(phase)
    label = phase_label(phase)
    icon  = TOMATO if phase == "work" else BREAK_ICON
    state = PAUSE_ICON if paused else PLAY_ICON

    # Big timer
    timer_text = Text(format_time(remaining), style=f"bold {color}", justify="center")
    timer_text.stylize("bold")

    # Progress bar (manual fill)
    elapsed = total - remaining
    pct = elapsed / total if total else 0
    bar_width = 38
    filled = int(pct * bar_width)
    bar = f"[{color}]{'█' * filled}[/{color}][dim]{'░' * (bar_width - filled)}[/dim]"

    # Pomodoro dots
    dots = ""
    for i in range(LONG_BREAK_EVERY):
        if i < cycle:
            dots += f"[{color}]{TOMATO}[/{color}] "
        else:
            dots += "[dim]○[/dim] "

    pomo_today, focus_secs = today_stats()
    focus_hrs = focus_secs // 3600
    focus_min = (focus_secs % 3600) // 60

    stats_grid = Table.grid(padding=(0, 2))
    stats_grid.add_column(justify="right")
    stats_grid.add_column(justify="left")
    stats_grid.add_row("[dim]Hoje[/dim]", f"[bold]{pomo_today}[/bold] [dim]pomodoros[/dim]")
    stats_grid.add_row("[dim]Foco[/dim]", f"[bold]{focus_hrs}h {focus_min:02d}m[/bold]")
    stats_grid.add_row("[dim]Total[/dim]", f"[bold]{pomo_count}[/bold] [dim]nesta sessão[/dim]")

    body = (
        f"\n"
        f" {state} [bold {color}]{label}[/bold {color}]\n\n"
        f" [bold {color}]{format_time(remaining)}[/bold {color}]\n\n"
        f" {bar}\n\n"
        f" {dots}\n"
    )

    main_panel = Panel(
        Align.center(body, vertical="middle"),
        title=f"[bold {color}]{icon} Pomodoro[/bold {color}]",
        border_style=color,
        padding=(1, 3),
    )

    controls = Panel(
        "[dim]  [bold]espaço[/bold] pausar/retomar   "
        "[bold]s[/bold] pular fase   "
        "[bold]q[/bold] sair[/dim]",
        border_style="dim",
        padding=(0, 1),
    )

    stats_panel = Panel(
        Align.center(stats_grid),
        title="[dim]Estatísticas[/dim]",
        border_style="dim",
        padding=(0, 2),
    )

    layout = Layout()
    layout.split_column(
        Layout(main_panel, name="main", ratio=5),
        Layout(stats_panel, name="stats", ratio=2),
        Layout(controls, name="controls", size=3),
    )
    return layout

# ── Main loop ─────────────────────────────────────────────────────────────
def run_phase(phase: str, minutes: int, pomo_count: int, cycle: int) -> tuple[bool, bool]:
    """Returns (completed, quit)."""
    total = minutes * 60
    remaining = total
    paused = False
    last_tick = time.time()

    with Live(
        build_layout(phase, remaining, total, paused, pomo_count, cycle),
        refresh_per_second=4,
        screen=True,
    ) as live:
        while remaining > 0:
            key = get_key()

            if key == "q":
                return False, True
            elif key == " ":
                paused = not paused
                last_tick = time.time()
            elif key in ("s", "S"):
                return False, False

            now = time.time()
            if not paused:
                elapsed = now - last_tick
                remaining = max(0, remaining - elapsed)
            last_tick = now

            live.update(build_layout(phase, int(remaining), total, paused, pomo_count, cycle))
            time.sleep(0.05)

    return True, False

def main():
    console.print(
        "\n[bold red]🍅 Pomodoro Terminal[/bold red] — [dim]iniciando...[/dim]\n",
        justify="center",
    )
    time.sleep(0.8)

    # Start key reader thread
    t = threading.Thread(target=_read_keys, daemon=True)
    t.start()

    pomo_count = 0
    cycle = 0  # pomodoros since last long break

    while True:
        # ── Work phase ──
        notify("🍅 Foco!", f"Sessão de {WORK_MINS} minutos começando.")
        completed, quit_ = run_phase("work", WORK_MINS, pomo_count, cycle)

        if quit_:
            break
        if completed:
            pomo_count += 1
            cycle += 1
            save_session("work", WORK_MINS * 60)
            notify("✅ Pomodoro completo!", "Hora de descansar.")

        # ── Break phase ──
        if cycle >= LONG_BREAK_EVERY:
            cycle = 0
            notify("☕ Pausa longa!", f"{LONG_BREAK_MINS} minutos de descanso.")
            completed, quit_ = run_phase("long", LONG_BREAK_MINS, pomo_count, cycle)
            if completed:
                save_session("long", LONG_BREAK_MINS * 60)
        else:
            notify("☕ Pausa curta!", f"{SHORT_BREAK_MINS} minutos.")
            completed, quit_ = run_phase("short", SHORT_BREAK_MINS, pomo_count, cycle)
            if completed:
                save_session("short", SHORT_BREAK_MINS * 60)

        if quit_:
            break

    # ── Goodbye ──
    pomo_today, focus_secs = today_stats()
    focus_min = focus_secs // 60
    console.print(
        f"\n[bold]Sessão encerrada![/bold] "
        f"[red]{pomo_count} pomodoros[/red] completados. "
        f"[dim]{focus_min} minutos de foco hoje.[/dim]\n",
        justify="center",
    )


if __name__ == "__main__":
    main()
