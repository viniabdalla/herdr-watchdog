#!/usr/bin/env python3
"""Remove links owned by this checkout; preserve all tasks and panel state."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bin-dir', type=Path, default=Path.home() / '.local/bin')
    parser.add_argument('--no-plugin', action='store_true')
    args = parser.parse_args()
    if not args.no_plugin:
        result = subprocess.run(['herdr', 'plugin', 'list', '--plugin', 'watchdog', '--json'],
                                check=True, capture_output=True, text=True)
        data = json.loads(result.stdout).get('result', {})
        plugins = data.get('plugins', [])
        if any(Path(p.get('plugin_root', '')).resolve() == ROOT for p in plugins):
            subprocess.run(['herdr', 'plugin', 'unlink', 'watchdog'], check=True)
    link = args.bin_dir.expanduser() / 'watchdog'
    if link.is_symlink() and link.resolve() == ROOT / 'watchdog':
        link.unlink()
        print('Removed ' + str(link))


if __name__ == '__main__':
    main()
