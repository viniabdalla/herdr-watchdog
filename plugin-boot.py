#!/usr/bin/env python3
"""Herdr argv entry: select the installed runtime before importing curses/psutil."""
from pathlib import Path
import os
import subprocess
import sys

root=Path(__file__).resolve().parent
python=root/'.watchdog-runtime'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
if not python.exists():
    print('Watchdog dependencies unavailable. Run: '+sys.executable+' '+str(root/'install.py'),file=sys.stderr)
    raise SystemExit(2)
raise SystemExit(subprocess.call([str(python),str(root/'watchdog'),*sys.argv[1:]]))
