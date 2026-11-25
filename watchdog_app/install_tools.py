"""External commands offered by the interactive Watchdog installer."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.request import urlretrieve


def ask(question):
    while True:
        try:
            answer = input(question + ' [s/N] ').strip().casefold()
        except EOFError:
            return False
        if answer in ('s', 'sim', 'y', 'yes'):
            return True
        if answer in ('', 'n', 'não', 'nao', 'no'):
            return False
        print('Responda s ou n.')


def herdr_ready():
    if not shutil.which('herdr'):
        return False
    result = subprocess.run(['herdr', '--version'], text=True, capture_output=True)
    version = re.search(r'\b(\d+)\.(\d+)\.(\d+)\b', result.stdout)
    return result.returncode == 0 and version and tuple(map(int, version.groups())) >= (0, 9, 1)


def install_herdr():
    if shutil.which('pacman') and subprocess.run(
            ['pacman', '-Si', 'herdr'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        subprocess.run(['sudo', 'pacman', '-S', 'herdr'], check=True)
    elif shutil.which('brew'):
        installed = subprocess.run(['brew', 'list', '--versions', 'herdr'], capture_output=True, text=True)
        action = 'upgrade' if installed.stdout.strip() else 'install'
        subprocess.run(['brew', action, 'herdr'], check=True)
    else:
        windows = sys.platform == 'win32'
        name = 'install.ps1' if windows else 'install.sh'
        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder)/name
            urlretrieve('https://herdr.dev/' + name, script)
            shell = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File'] if windows else ['sh']
            subprocess.run([*shell, str(script)], check=True)
        # The official installer can add a directory for future shells.
        default = (Path(os.environ['LOCALAPPDATA'])/'Programs/Herdr/bin' if windows
                   else Path.home()/'.local/bin')
        directory = os.environ.get('HERDR_INSTALL_DIR') or str(default)
        os.environ['PATH'] = directory + os.pathsep + os.environ.get('PATH', '')


def install_yazi():
    if shutil.which('pacman'):
        command = ['sudo', 'pacman', '-S', 'yazi']
    elif shutil.which('brew'):
        installed = subprocess.run(['brew', 'list', '--versions', 'yazi'],
                                   capture_output=True, text=True)
        action = 'reinstall' if installed.stdout.strip() else 'install'
        command = ['brew', action, 'yazi']
    elif sys.platform == 'win32' and shutil.which('winget'):
        command = ['winget', 'install', '--exact', '--id', 'sxyazi.yazi']
    elif shutil.which('mise'):
        command = ['mise', 'use', '-g', 'yazi']
    elif shutil.which('apt-cache') and subprocess.run(
            ['apt-cache', 'show', 'yazi'], capture_output=True).returncode == 0:
        command = ['sudo', 'apt-get', 'install', '--reinstall', 'yazi']
    elif shutil.which('cargo'):
        command = ['cargo', 'install', '--force', 'yazi-build']
    else:
        raise RuntimeError('Instale Yazi e ya seguindo https://yazi-rs.github.io/docs/installation/')
    subprocess.run(command, check=True)


def offer_yazi():
    missing = [name for name in ('yazi', 'ya') if not shutil.which(name)]
    if not missing:
        return
    if ask('Falta: ' + ', '.join(missing) + '. Instalar o pacote Yazi (yazi e ya)?'):
        try:
            install_yazi()
        except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
            print('Instalação do Yazi incompleta:', error)
    if not shutil.which('yazi'):
        print('Files precisa do Yazi. Tasks e Progress continuam disponíveis.')
    elif not shutil.which('ya'):
        print('Sem ya, Artifacts não consegue revelar arquivos no Files.')


def offer_pane_ids():
    from . import pane_ids_install as ids

    if not sys.platform.startswith('linux') or not shutil.which('systemctl'):
        print('Os IDs na borda requerem Linux com systemd de usuário.')
        return
    result = subprocess.run([*ids.SYSTEMCTL, 'show', ids.SERVICE, '-p', 'LoadState', '--value'],
                            capture_output=True, text=True)
    state = result.stdout.strip()
    if state not in ('loaded', 'not-found'):
        print('Serviço de IDs indisponível nesta sessão:', result.stderr.strip() or state)
        return
    active = [*ids.SYSTEMCTL, 'is-active', '--quiet', ids.SERVICE]
    if state == 'loaded' and subprocess.run(active).returncode == 0:
        return
    question = ('Ativar o serviço herdr-pane-ids instalado?' if state == 'loaded' else
                'Mostrar o ID na borda de cada pane? Instalar e ativar herdr-pane-ids?')
    if not ask(question):
        return
    try:
        if state == 'not-found':
            ids.install()
        subprocess.run([*ids.SYSTEMCTL, 'enable', '--now', ids.SERVICE], check=True)
        subprocess.run(active, check=True)
        print('IDs dos panes ativados.')
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print('Não foi possível ativar os IDs dos panes:', error)


def prepare_tools():
    if not herdr_ready():
        if not ask('Instalar o Herdr 0.9.1 ou superior para usar o Watchdog?'):
            raise RuntimeError('O painel precisa do Herdr 0.9.1 ou superior. Instalação cancelada.')
        install_herdr()
        if not herdr_ready():
            raise RuntimeError('Herdr 0.9.1 ou superior ainda indisponível no PATH.')
    offer_yazi()
    offer_pane_ids()
