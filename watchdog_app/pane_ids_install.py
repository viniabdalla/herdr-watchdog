"""Install the bundled herdr-pane-ids helper for the current systemd user."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

SOURCE = Path(__file__).resolve().parents[1]/'extras/herdr-pane-ids'
SERVICE = 'herdr-pane-ids.service'
SYSTEMCTL = ['systemctl', '--user']


def with_borders(config):
    # Keep other tables and comments intact. Insert missing keys in [ui].
    header = re.search(r'^\s*\[ui\][ \t]*(?:#[^\n]*)?$', config, re.M)
    if not header:
        config = config.rstrip() + '\n\n[ui]\n'
        header = re.search(r'^\[ui\]$', config, re.M)
    start = header.end()
    following = re.search(r'^[ \t]*\[', config[start:], re.M)
    end = start + following.start() if following else len(config)
    section = config[start:end]
    for key, value in [('pane_outer_borders', 'true'), ('pane_borders', '"always"')]:
        assignment = rf'^([ \t]*{key}[ \t]*=[ \t]*)[^\n#]*?([ \t]*(?:#[^\n]*)?)$'
        section, count = re.subn(assignment, rf'\g<1>{value}\g<2>', section, flags=re.M)
        if not count:
            section = '\n' + key + ' = ' + value + '\n' + section
    return config[:start] + section + config[end:]


def configure_borders(cfg):
    cfg.parent.mkdir(parents=True, exist_ok=True)
    old = cfg.read_text() if cfg.exists() else ''
    new = with_borders(old)
    if 'herdr-pane-ids copy' not in old and not re.search(r"""['"]prefix\+y['"]""", old, re.I):
        new += ('\n[[keys.command]]\nkey = "prefix+y"\ntype = "popup"\n'
                'command = "herdr-pane-ids copy"\nwidth = 30\nheight = 4\n')
    if new == old:
        return
    with tempfile.NamedTemporaryFile(dir=cfg.parent, delete=False, mode='w') as out:
        candidate = Path(out.name)
        out.write(new)
    try:
        subprocess.run(['herdr', 'config', 'check'], check=True,
                       env=dict(os.environ, HERDR_CONFIG_PATH=str(candidate)))
        if cfg.is_file():
            if cfg.read_text() != old:
                raise RuntimeError(f'A configuração mudou durante a instalação: {cfg}')
            backup = cfg.with_name(cfg.name+'.bak-herdr-pane-ids')
            if not backup.exists():
                shutil.copy2(cfg, backup)
            shutil.copymode(cfg, candidate)
        candidate.replace(cfg)
    finally:
        candidate.unlink(missing_ok=True)


def install():
    home = Path.home()
    config_home = Path(os.environ.get('XDG_CONFIG_HOME') or home/'.config')
    binary = home/'.local/bin/herdr-pane-ids'
    unit = config_home/'systemd/user'/SERVICE
    cfg = Path(os.environ.get('HERDR_CONFIG_PATH') or config_home/'herdr/config.toml')
    herdr_dir = str(Path(shutil.which('herdr')).parent)
    service_path = herdr_dir.replace('%', '%%').replace('\\', '\\\\').replace('"', '\\"')
    unit_text = (SOURCE/SERVICE).read_text().replace('Environment=PATH=/usr/bin:/bin',
                                f'Environment="PATH={service_path}:/usr/bin:/bin"')
    files = {binary: ((SOURCE/binary.name).read_bytes(), 0o755), unit: (unit_text.encode(), 0o644)}
    for path, (content, _) in files.items():
        if (path.is_symlink() or path.exists()) and (not path.is_file() or path.read_bytes() != content):
            raise RuntimeError(f'Já existe outra instalação em {path}.')

    configure_borders(cfg.expanduser().resolve())
    for path, (content, mode) in files.items():
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=path.parent) as out:
                out.write(content)
                out.flush()
                os.fchmod(out.fileno(), mode)
                os.link(out.name, path)
    subprocess.run(SYSTEMCTL + ['daemon-reload'], check=True)
    # A first-time install can precede the first Herdr server.
    subprocess.run(['herdr', 'server', 'reload-config'], stdout=subprocess.DEVNULL, check=False)
