"""Presentation labels derived only from verified account paths; no file reads."""
from collections import Counter
from pathlib import Path


def printable_text(value):
    """Use the same control-character replacement for comparison and rendering."""
    return ''.join(c if c.isprintable() else ' ' for c in str(value))


def account_labels(accounts):
    """Extend colliding printable names; number irreducibly identical paths."""
    paths = [Path(account).expanduser() for account in accounts]
    defaults = {Path.home() / '.codex', Path.home() / '.claude'}
    custom = sorted(set(paths) - defaults, key=str)
    depths = dict.fromkeys(custom, 1)
    labels = {path: printable_text(path.name or str(path)) for path in custom}
    numbers = {path: number for number, path in enumerate(custom, 1)}
    while True:
        counts = Counter(labels.values())
        collisions = [path for path in custom
                      if counts[labels[path]] > 1 or labels[path] == 'Default account']
        if not collisions:
            break
        for path in collisions:
            if depths[path] < len(path.parts):
                depths[path] += 1
                labels[path] = printable_text(Path(*path.parts[-depths[path]:]))
            else:
                # Raw paths may differ only in controls replaced with spaces.
                # Sorted path numbers are stable across row order and duplicates.
                labels[path] += f' [account {numbers[path]}]'
    return ['Default account' if path in defaults else labels[path] for path in paths]
