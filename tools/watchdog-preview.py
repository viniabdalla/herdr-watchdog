#!/usr/bin/env python3
"""Interactive Tasks entrypoint and the Progress/Artifacts preview, stdlib only.

Run: python3 tools/watchdog-preview.py tasks|progress|artifacts --repo PATH
Tasks uses confirmed TODO edits and review proposals; the other views are read-only.
No panel writes Left Undone state.
"""
import argparse
import curses
import json
from pathlib import Path
import re
import shutil
import subprocess
import textwrap
import unicodedata
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def plain(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text)
                   if not unicodedata.combining(c)).lower()


def read_tasks(repo):
    from watchdog_app.todo import Snapshot, SECTIONS
    groups = {section: [] for section in SECTIONS}
    for task in Snapshot.read(repo).tasks:
        groups[task.section].append((task.done, task.text))
    return groups


def bar(done, total, width):
    size = max(4, min(28, width - 20))
    filled = int(size * done / total) if total else 0
    return '[' + '#' * filled + '-' * (size - filled) + f'] {done}/{total}'


def artifact_path(repo, name):
    path = (repo / name).resolve()
    if not path.is_relative_to(repo) or not path.is_file():
        raise ValueError('Artifact must be an existing file inside this project')
    return path


def contents(repo, mode, width):
    if mode == 'artifacts':
        entries = json.loads((repo / 'docs/preview-artifacts.json').read_text())
        rows = [('Manual artifact list — automatic tracking not connected', None), ('', None)]
        for item in entries:
            rows.append((f"{item['path']} · {item['agent']}", item['path']))
            rows.append(('  ' + item['summary'], item['path']))
            rows.append(('', None))
        return rows
    groups = read_tasks(repo)
    tasks = [task for group in groups.values() for task in group]
    done = sum(checked for checked, _ in tasks)
    if mode == 'tasks':
        rows = [('Source: TODO.md · read only · refreshes every second', None), ('', None)]
        for section, items in groups.items():
            rows.append((section.upper() + f' ({len(items)})', None))
            for checked, text in items:
                rows.append((('[x] ' if checked else '[ ] ') + text, None))
            if not items:
                rows.append(('  None', None))
            rows.append(('', None))
        return rows
    # Progress is native and bound; the manual preview checklist is retired.
    from watchdog_app.progress_ui import rows
    return [(text, None) for text, _, _ in rows(repo, width=width)]


def draw_text(screen, y, x, text, attr=0):
    height, width = screen.getmaxyx()
    if y < 0 or y >= height or x >= width - 1:
        return
    # Files and task titles are data, never terminal escape sequences.
    text = ''.join(c if c.isprintable() else ' ' for c in str(text))
    try:
        screen.addnstr(y, x, text, max(0, width - x - 1), attr)
    except curses.error:
        pass


def browse(path, client_id):
    # Receiver 0 broadcasts to every Yazi. Only address the linked Files pane.
    if not client_id or not client_id.isdecimal() or not 0 < int(client_id) < 2**64:
        raise ValueError('No linked Files pane; start it with a unique Yazi client ID')
    if not shutil.which('ya'):
        raise ValueError('Yazi CLI (ya) is not installed')
    subprocess.run(['ya', 'emit-to', client_id, 'reveal', str(path)],
                   check=True, timeout=3, stdout=subprocess.DEVNULL,
                   stderr=subprocess.PIPE, text=True)


def panel(screen, repo, mode, yazi_client_id=None):
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    screen.timeout(1000)
    curses.mousemask(curses.ALL_MOUSE_EVENTS)
    selected = 0
    offset = 0
    message = ''
    while True:
        height, width = screen.getmaxyx()
        screen.erase()
        draw_text(screen, 0, 0, 'WATCHDOG MVP / ' + mode.upper(), curses.A_BOLD)
        draw_text(screen, 1, 0, repo.name + ' · disposable preview')
        try:
            source = contents(repo, mode, width)
        except (OSError, ValueError, KeyError, TypeError) as error:
            source = [('Cannot read source: ' + str(error), None)]
        rows = []
        for text, path in source:
            clean = ''.join(c if c.isprintable() else ' ' for c in text)
            rows.extend((part, path) for part in textwrap.wrap(
                clean, max(4, width - 3), subsequent_indent='  ') or [''])
        selected = min(selected, max(0, len(rows) - 1))
        page = max(1, height - 5)
        offset = min(offset, selected)
        if selected >= offset + page:
            offset = selected - page + 1
        for index, (text, _) in enumerate(rows[offset:offset + page], offset):
            attr = curses.A_REVERSE if index == selected else 0
            draw_text(screen, index - offset + 3, 0, text, attr)
        footer = 'j/k scroll · q exit'
        if mode == 'artifacts':
            footer += ' · Enter/click: reveal in Files'
        draw_text(screen, height - 1, 0, message or footer, curses.A_DIM)
        screen.refresh()
        key = screen.getch()
        message = ''
        if key in (ord('q'), 27):
            return
        if key in (ord('j'), curses.KEY_DOWN):
            selected += 1
        elif key in (ord('k'), curses.KEY_UP):
            selected = max(0, selected - 1)
        elif key in (curses.KEY_NPAGE, ord(' ')):
            selected += page
        elif key == curses.KEY_PPAGE:
            selected = max(0, selected - page)
        elif key == curses.KEY_HOME:
            selected = 0
        elif key == curses.KEY_END:
            selected = len(rows) - 1
        elif key == curses.KEY_MOUSE:
            try:
                _, _, y, _, state = curses.getmouse()
                if 3 <= y < height - 2:
                    selected = min(len(rows) - 1, max(0, offset + y - 3))
                    if state & (curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED):
                        key = 10
            except curses.error:
                pass
        if key in (10, 13, curses.KEY_ENTER) and mode == 'artifacts' and rows:
            selected = min(selected, len(rows) - 1)
            path = rows[selected][1]
            if path:
                try:
                    browse(artifact_path(repo, path), yazi_client_id)
                    message = 'Revealed in Files'
                except (OSError, ValueError, subprocess.SubprocessError) as error:
                    message = str(error)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('tasks', 'progress', 'artifacts'))
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--yazi-client-id', help='Client ID of the linked Yazi Files pane')
    parser.add_argument('--binding-file', type=Path)
    args = parser.parse_args()
    if args.mode == 'tasks':
        from watchdog_app.tasks_ui import run
        run(args.repo.resolve(), args.binding_file)
        return
    if args.mode == 'progress':
        from watchdog_app.progress_ui import run
        run(args.repo.resolve(), args.binding_file)
        return
    curses.wrapper(panel, args.repo.resolve(), args.mode, args.yazi_client_id)


if __name__ == '__main__':
    main()
