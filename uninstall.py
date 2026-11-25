#!/usr/bin/env python3
"""Remove links owned by this checkout; preserve all tasks and panel state."""
import argparse
import json
from pathlib import Path
import subprocess
import os
from watchdog_app.installation import account_root, owned_skill, check_launcher

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bin-dir', type=Path, default=Path.home() / '.local/bin')
    parser.add_argument('--no-plugin', action='store_true')
    parser.add_argument('--codex-skills-dir', type=Path)
    args = parser.parse_args()
    if not args.no_plugin:
        result = subprocess.run(['herdr', 'plugin', 'list', '--plugin', 'watchdog', '--json'],
                                check=True, capture_output=True, text=True)
        data = json.loads(result.stdout).get('result', {})
        plugins = data.get('plugins', [])
        if any(Path(p.get('plugin_root', '')).resolve() == ROOT for p in plugins):
            subprocess.run(['herdr', 'plugin', 'unlink', 'watchdog'], check=True)
    link = args.bin_dir.expanduser() / ('watchdog.cmd' if os.name == 'nt' else 'watchdog')
    try:
        check_launcher(link)
    except RuntimeError:
        pass
    else:
        if link.exists() or link.is_symlink():
            link.unlink()
            print('Removed ' + str(link))
    skill = (args.codex_skills_dir or account_root()/'skills').expanduser()/'religar'
    if owned_skill(skill):
        (skill/'SKILL.md').unlink(missing_ok=True)
        (skill/'.watchdog-install.json').unlink()
        if not any(skill.iterdir()): skill.rmdir()


if __name__ == '__main__':
    main()
