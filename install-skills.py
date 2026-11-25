#!/usr/bin/env python3
"""Install the bundled merge-danger skill for both harnesses in this checkout.

Override the destinations for account installations or isolated verification.
Existing unrelated skills are preserved.
"""
import argparse
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--claude-skills-dir', type=Path, default=ROOT/'.claude/skills')
    parser.add_argument('--codex-skills-dir', type=Path, default=ROOT/'.agents/skills')
    args = parser.parse_args()
    source = ROOT/'skills/merge-danger'
    targets = list(dict.fromkeys(root.expanduser().absolute()/'merge-danger'
                                for root in (args.claude_skills_dir, args.codex_skills_dir)))
    for target in targets:
        if target.exists() or target.is_symlink():
            if not target.is_symlink() or target.resolve() != source:
                parser.error('Refusing to overwrite another skill: ' + str(target))
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_symlink():
            target.symlink_to(os.path.relpath(source, target.parent),
                              target_is_directory=True)
        print('Installed ' + str(target))


if __name__ == '__main__':
    main()
