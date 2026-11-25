#!/usr/bin/env python3
"""Install Watchdog and Religar for the active Codex account."""
import argparse
from pathlib import Path
import subprocess
import sys
from watchdog_app.installation import (ROOT, account_root, check_launcher, check_skill,
                                       install_skill, launcher_text, runtime_python)
from watchdog_app.install_tools import prepare_tools
import os


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bin-dir',type=Path,default=Path.home()/'.local/bin')
    parser.add_argument('--codex-skills-dir',type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--no-plugin', action='store_true', help='Prepare launcher and skill without system prompts or plugin link')
    modes.add_argument('--plugin-build', action='store_true', help='Build from Herdr; offer tools when a terminal is attached')
    modes.add_argument('--tools-only', action='store_true', help='Offer Herdr, Yazi and pane IDs without reinstalling Watchdog')
    parser.add_argument('--skip-dependencies',action='store_true',help='Use current Python; dependencies must already be available')
    args=parser.parse_args()
    target=args.bin_dir.expanduser()/('watchdog.cmd' if os.name=='nt' else 'watchdog')
    skill=(args.codex_skills_dir or account_root()/'skills').expanduser()/'religar'
    link_plugin = not (args.no_plugin or args.plugin_build)
    interactive_build = args.plugin_build and sys.stdin.isatty() and sys.stdout.isatty()
    try:
        if args.tools_only:
            prepare_tools()
            return
        check_launcher(target);check_skill(skill)
        if link_plugin or interactive_build:
            prepare_tools()
        python=runtime_python(skip_dependencies=args.skip_dependencies)
        if link_plugin:
            subprocess.run(['herdr','plugin','link',str(ROOT)],check=True)
        install_skill(skill,python)
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.is_symlink():target.unlink()
        target.write_text(launcher_text(python,windows=os.name=='nt'))
        target.chmod(0o755)
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        parser.error(str(error))
    print('Installed '+str(target)+' and '+str(skill))
    if args.plugin_build and not interactive_build:
        print('Para configurar os aplicativos no terminal, execute install.py --tools-only neste checkout.')


if __name__=='__main__':main()
