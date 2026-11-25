"""Install owned launchers/skills without symlink privileges or shell splitting."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import venv
from .compat import shell_command

ROOT = Path(__file__).resolve().parents[1]
OWNER = '.watchdog-install.json'


def account_root():
    return Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex'))).expanduser().resolve()


def python_path(root):
    return root/('Scripts/python.exe' if os.name=='nt' else 'bin/python')


def runtime_python(*, skip_dependencies=False):
    if skip_dependencies:
        return Path(sys.executable)
    directory = ROOT/'.watchdog-runtime'
    python = python_path(directory)
    if not python.is_file():
        venv.EnvBuilder(with_pip=True).create(directory)
    requirements=['psutil>=5.9,<8']
    if os.name=='nt':
        requirements.append('windows-curses>=2.4,<3')
    subprocess.run([str(python),'-m','pip','install',*requirements],check=True)
    subprocess.run([str(python),'-c','import psutil, curses'],check=True)
    return python


def owned_skill(target):
    try:
        return json.loads((target/OWNER).read_text()) == {'root':str(ROOT)}
    except (OSError, ValueError):
        return False


def check_skill(target):
    if (target.exists() or target.is_symlink()) and not owned_skill(target):
        raise RuntimeError('Refusing to overwrite another skill: '+str(target))


def install_skill(target, python):
    check_skill(target)
    target.mkdir(parents=True,exist_ok=True)
    source=(ROOT/'skills/religar/SKILL.md').read_text()
    command=shell_command([str(python),str(ROOT/'watchdog'),'religar'])+' <ref>'
    (target/'SKILL.md').write_text(source.replace('`watchdog religar <ref>`','`'+command+'`'),encoding='utf-8')
    (target/OWNER).write_text(json.dumps({'root':str(ROOT)}))


def launcher_text(python, *, windows=False):
    if windows:
        return '@echo off\r\nrem watchdog-owned: '+str(ROOT)+'\r\n"'+str(python)+'" "'+str(ROOT/'watchdog')+'" %*\r\n'
    return '#!/bin/sh\n# watchdog-owned: '+str(ROOT)+'\nexec '+shlex.join([str(python),str(ROOT/'watchdog')])+' "$@"\n'


def check_launcher(target):
    if not (target.exists() or target.is_symlink()):
        return
    if target.is_symlink() and target.resolve()==ROOT/'watchdog':
        return
    if not target.is_symlink() and ('watchdog-owned: '+str(ROOT)+'\n') in target.read_text():
        return
    raise RuntimeError('Refusing to overwrite another command: '+str(target))
