#!/usr/bin/env python3
"""Link this checkout into PATH and Herdr without overwriting another command."""
import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bin-dir', type=Path, default=Path.home() / '.local/bin')
    parser.add_argument('--no-plugin', action='store_true')
    args = parser.parse_args()
    target = args.bin_dir.expanduser() / 'watchdog'
    if target.exists() or target.is_symlink():
        if not target.is_symlink() or target.resolve() != ROOT / 'watchdog':
            parser.error('Refusing to overwrite another command: ' + str(target))
    if not args.no_plugin:
        from watchdog_app.bindings import engine
        engine()
        # Link the plugin before exposing the command, so a failed Herdr link
        # does not leave a misleadingly installed launcher.
        subprocess.run(['herdr', 'plugin', 'link', str(ROOT)], check=True)
    (ROOT / 'watchdog').chmod(0o755)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.is_symlink():
        target.symlink_to(ROOT / 'watchdog')
    print('Installed ' + str(target))


if __name__ == '__main__':
    main()
