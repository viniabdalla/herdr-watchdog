"""Orchestrate checkpoint: show pending project changes, then save them in one local commit.

The user sees the exact file list in the confirmation. Confirming commits exactly
that list (never pushes); a list that changed since confirmation is refused.
"""
import os
import subprocess
from pathlib import Path

LABELS = {'M': 'Modified', 'A': 'Added', 'D': 'Deleted', 'R': 'Renamed', 'C': 'Copied',
          'T': 'Type changed', 'U': 'Conflict', '?': 'New'}


def git(repo, *args, timeout=30):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True,
                            timeout=timeout, env=env)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip() or 'git failed')
    return result.stdout


def is_repo(repo):
    try:
        return git(repo, 'rev-parse', '--show-toplevel').strip() == str(Path(repo).resolve())
    except (RuntimeError, OSError):
        return False


def pending(repo):
    """Exact working-tree changes as (code, path), untracked files listed individually."""
    if not is_repo(repo):
        return None
    raw = git(repo, 'status', '--porcelain=v1', '-z', '--untracked-files=all')
    entries, parts = [], raw.split('\0')
    i = 0
    while i < len(parts):
        item = parts[i]
        i += 1
        if not item:
            continue
        code, path = item[:2], item[3:]
        if code[0] in 'RC':
            i += 1  # Skip the rename source.
        entries.append((code, path))
    return entries


def describe(entries):
    rows = []
    for code, path in entries:
        key = '?' if code == '??' else 'U' if 'U' in code else (code[0] if code[0] != ' ' else code[1])
        rows.append(LABELS.get(key, 'Changed') + ': ' + path)
    return rows


def conflicted(entries):
    return [path for code, path in entries if 'U' in code or code in ('AA', 'DD')]


def commit(repo, expected, message):
    """Commit exactly the confirmed change list; returns {'sha', 'files', 'created'}."""
    current = pending(repo)
    if current is None:
        return None
    if current != expected:
        raise RuntimeError('Project files changed after confirmation; review the checkpoint again')
    head = git(repo, 'rev-parse', 'HEAD').strip()
    if not current:
        return {'sha': head, 'files': [], 'created': False}
    if conflicted(current):
        raise RuntimeError('Resolve merge conflicts first: ' + ', '.join(conflicted(current)))
    git(repo, 'add', '-A', '--', '.')
    git(repo, 'commit', '-q', '-m', message)
    sha = git(repo, 'rev-parse', 'HEAD').strip()
    if pending(repo):
        raise RuntimeError('Checkpoint ' + sha[:8] + ' was created, but new changes appeared meanwhile')
    return {'sha': sha, 'files': [path for _, path in current], 'created': True, 'parent': head}
