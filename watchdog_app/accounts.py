"""Presentation labels derived only from verified account paths; no file reads."""
from pathlib import Path


def account_labels(accounts):
    """Return a label per path, extending ambiguous basenames with parent names."""
    paths = [Path(account).expanduser() for account in accounts]
    defaults = {Path.home() / '.codex', Path.home() / '.claude'}
    custom = set(paths) - defaults
    labels = {}
    for path in custom:
        for depth in range(1, len(path.parts) + 1):
            suffix = path.parts[-depth:]
            if not any(other != path and other.parts[-depth:] == suffix for other in custom):
                break
        labels[path] = '/'.join(suffix)
    return ['Default account' if path in defaults else labels[path] for path in paths]
