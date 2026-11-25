#!/usr/bin/env python3
"""Install Watchdog and Religar for the active Codex account."""
import argparse
from pathlib import Path
import subprocess
from watchdog_app.installation import (ROOT, account_root, check_launcher, check_skill,
                                       install_skill, launcher_text, runtime_python)
import os


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bin-dir',type=Path,default=Path.home()/'.local/bin')
    parser.add_argument('--codex-skills-dir',type=Path)
    parser.add_argument('--no-plugin',action='store_true')
    parser.add_argument('--skip-dependencies',action='store_true',help='Use current Python; dependencies must already be available')
    args=parser.parse_args()
    target=args.bin_dir.expanduser()/('watchdog.cmd' if os.name=='nt' else 'watchdog')
    skill=(args.codex_skills_dir or account_root()/'skills').expanduser()/'religar'
    try:
        check_launcher(target);check_skill(skill)
        python=runtime_python(skip_dependencies=args.skip_dependencies)
        if not args.no_plugin:
            subprocess.run(['herdr','plugin','link',str(ROOT)],check=True)
        install_skill(skill,python)
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.is_symlink():target.unlink()
        target.write_text(launcher_text(python,windows=os.name=='nt'))
        target.chmod(0o755)
    except RuntimeError as error:
        parser.error(str(error))
    print('Installed '+str(target)+' and '+str(skill))


if __name__=='__main__':main()
