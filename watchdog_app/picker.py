"""Terminal selectors. Escape returns before any layout mutation."""
import curses
from .layouts import PRESETS


def text(screen, row, col, value, attr=0):
    h, w = screen.getmaxyx()
    if not 0 <= row < h or col >= w - 1:
        return
    value = ''.join(c if c.isprintable() else ' ' for c in str(value))
    try:
        screen.addnstr(row, col, value, max(0, w - col - 1), attr)
    except curses.error:
        pass


def setup(screen):
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    screen.keypad(True)


def choose_layout(screen, default=2):
    setup(screen)
    selected = default if default in PRESETS else 2
    while True:
        screen.erase()
        h, w = screen.getmaxyx()
        text(screen, 0, 0, 'Watchdog / Choose layout', curses.A_BOLD)
        split = min(34, max(12, w // 2))
        for index, (number, (name, _)) in enumerate(PRESETS.items()):
            text(screen, 3 + index * 2, 0, f'{number}. {name}'[:split - 2],
                 curses.A_REVERSE if number == selected else 0)
        for index, line in enumerate(PRESETS[selected][1].splitlines()):
            text(screen, 3 + index, split, line)
        text(screen, h - 3, 0, 'Optional Left Undone stays beside Files.')
        text(screen, h - 2, 0, 'Arrows / j k: choose   Enter: apply   Esc: cancel')
        screen.refresh()
        key = screen.getch()
        if key in (27, ord('q')):
            return None
        if key in (10, 13, curses.KEY_ENTER):
            return selected
        if key in (ord('j'), curses.KEY_DOWN):
            selected = selected % 4 + 1
        elif key in (ord('k'), curses.KEY_UP):
            selected = (selected - 2) % 4 + 1
        elif key in (ord('1'), ord('2'), ord('3'), ord('4')):
            selected = key - ord('0')


def choose_conversation(screen, choices):
    setup(screen)
    selected = 0
    while True:
        screen.erase()
        h, _ = screen.getmaxyx()
        text(screen, 0, 0, 'Watchdog / Choose conversation', curses.A_BOLD)
        start = max(0, selected - max(1, h - 5) + 1)
        for index, binding in enumerate(choices[start:start + max(1, h - 5)], start):
            text(screen, 2 + index - start, 0,
                 f'{binding.kind} · {binding.pane} · {binding.session}',
                 curses.A_REVERSE if index == selected else 0)
        text(screen, h - 2, 0, 'Arrows / j k: choose   Enter: continue   Esc: cancel')
        screen.refresh()
        key = screen.getch()
        if key in (27, ord('q')):
            return None
        if key in (10, 13, curses.KEY_ENTER):
            return choices[selected]
        if key in (ord('j'), curses.KEY_DOWN):
            selected = (selected + 1) % len(choices)
        elif key in (ord('k'), curses.KEY_UP):
            selected = (selected - 1) % len(choices)
