"""Instalação interativa aprovada pelo Vini; processos e HOME isolados."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InstallToolsTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        self.bin = self.home / 'bin'
        self.bin.mkdir()
        self.env = dict(os.environ, HOME=tmp.name, PATH=str(self.bin),
                        CODEX_HOME=str(self.home/'account'), XDG_CONFIG_HOME=str(self.home/'.config'),
                        HERDR_CONFIG_PATH=str(self.home/'.config/herdr/config.toml'), LOG=str(self.home/'log'))
        self.launcher = self.home/'.local/bin/watchdog'
        self.tool('python3', 'exec "' + sys.executable + '" "$@"')

    def tool(self, name, script=':'):
        path = self.bin / name
        path.write_text('#!/bin/sh\n' + script + '\n')
        path.chmod(0o755)

    def install(self, answers='', *options):
        return subprocess.run([sys.executable, str(ROOT/'install.py'), '--skip-dependencies',
                               *options], env=self.env, input=answers, capture_output=True,
                              text=True, timeout=10)

    def test_declining_herdr_stops_before_any_install(self):
        result = self.install('n\n')
        self.assertIn('Instalar o Herdr', result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.launcher.exists())
        self.assertFalse((self.home/'account').exists())
        self.assertNotIn('Traceback', result.stderr)

    def installed_herdr(self):
        self.tool('herdr', 'if [ "$1" = --version ]; then echo "herdr 0.9.1"; else echo "$*" >> "$LOG"; fi')

    def test_decline_only_missing_ya_keeps_watchdog(self):
        self.installed_herdr()
        self.tool('yazi')
        result = self.install('n\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Falta: ya.', result.stdout)
        self.assertIn('Artifacts', result.stdout)
        self.assertTrue(self.launcher.is_file())

    def test_accept_installs_herdr_and_yazi_and_checks_binaries(self):
        self.tool('pacman')
        self.tool('sudo', '''case "$3" in
herdr) echo '#!/bin/sh' > "$HOME/bin/herdr"
       echo 'echo herdr 0.9.1' >> "$HOME/bin/herdr"
       /bin/chmod +x "$HOME/bin/herdr";;
yazi) /bin/cp "$HOME/bin/pacman" "$HOME/bin/yazi"
      /bin/cp "$HOME/bin/pacman" "$HOME/bin/ya";;
esac''')
        result = self.install('s\ns\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.bin/'ya').exists())
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('[s/N]', result.stdout)

    def test_optional_install_failure_keeps_watchdog_and_reports_files_limit(self):
        self.installed_herdr()
        self.tool('pacman')
        self.tool('sudo', 'exit 1')
        result = self.install('s\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Files', result.stdout)
        self.assertTrue(self.launcher.is_file())

    def systemd(self, state):
        self.tool('systemctl', '''echo "$*" >> "$LOG"
case "$2" in
  show) echo ''' + ('not-found' if state == 'absent' else 'loaded') + ''';;
  is-active) test -f "$HOME/active";;
  enable) /usr/bin/touch "$HOME/active";;
esac''')
        if state == 'active':
            (self.home/'active').touch()
        self.installed_herdr()
        self.tool('yazi')
        self.tool('ya')

    @unittest.skipUnless(sys.platform.startswith('linux'), 'systemd de usuário')
    def test_existing_service_only_activates_after_opt_in(self):
        self.systemd('inactive')
        self.tool('herdr-pane-ids')
        refused = self.install('n\n')
        self.assertIn('Ativar', refused.stdout)
        self.assertFalse((self.home/'active').exists())
        accepted = self.install('s\n')
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertTrue((self.home/'active').is_file())
        again = self.install()
        self.assertNotIn('[s/N]', again.stdout)
        self.assertEqual((self.home/'log').read_text().count('enable --now'), 1)

    @unittest.skipUnless(sys.platform.startswith('linux'), 'systemd de usuário')
    def test_optional_pane_ids_installs_service_and_config_only_on_accept(self):
        self.systemd('absent')
        cfg = self.home/'.config/herdr/config.toml'
        cfg.parent.mkdir(parents=True)
        cfg.write_text('[ui]\npane_outer_borders = false\n')
        before = cfg.read_text()
        refused = self.install('n\n')
        self.assertIn('Mostrar o ID', refused.stdout)
        self.assertEqual(cfg.read_text(), before)
        accepted = self.install('s\n')
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertTrue((self.home/'active').is_file(), accepted.stdout)
        self.assertTrue((self.home/'.local/bin/herdr-pane-ids').is_file())
        self.assertIn('pane_outer_borders = true', cfg.read_text())
        self.assertIn('herdr-pane-ids copy', cfg.read_text())
        self.assertTrue((self.home/'.config/systemd/user/herdr-pane-ids.service').is_file())

    def test_tools_only_after_plugin_build_does_not_change_launcher(self):
        self.installed_herdr()
        self.tool('yazi')
        self.tool('ya')
        result = self.install('', '--tools-only')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.launcher.exists())
        self.assertFalse((self.home/'account').exists())
        self.assertFalse((self.home/'log').exists())

    @unittest.skipUnless(sys.platform.startswith('linux'), 'systemd de usuário')
    def test_invalid_config_keeps_original_and_does_not_partly_enable_service(self):
        self.systemd('absent')
        self.tool('herdr', 'case "$1" in --version) echo "herdr 0.9.1";; config) exit 1;; esac')
        config = self.home/'custom.toml'
        config.write_text('original')
        self.env['HERDR_CONFIG_PATH'] = str(config)
        result = self.install('s\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Não foi possível ativar', result.stdout)
        self.assertEqual(config.read_text(), 'original')
        self.assertFalse((self.home/'active').exists())
        self.assertFalse((self.home/'.config/systemd/user/herdr-pane-ids.service').exists())

    @unittest.skipUnless(sys.platform.startswith('linux'), 'systemd de usuário')
    def test_existing_copy_shortcut_and_unrelated_tables_survive(self):
        self.systemd('absent')
        cfg = self.home/'custom.toml'
        self.env['HERDR_CONFIG_PATH'] = str(cfg)
        original = ('[ui]\npane_outer_borders = false # current setting\n'
                    '[menu]\npane_borders = "example"\n'
                    '[[keys.command]]\nkey = "prefix+y"\ncommand = "my-copy"\n')
        cfg.write_text(original)
        self.assertEqual(self.install('s\n').returncode, 0)
        text = cfg.read_text()
        self.assertIn('true # current setting', text)
        self.assertIn('pane_borders = "example"', text)
        self.assertEqual(text.count('prefix+y'), 1)
        self.assertEqual(cfg.with_name('custom.toml.bak-herdr-pane-ids').read_text(), original)

    def test_unattended_plugin_build_works_without_system_tools_or_prompts(self):
        result = self.install('', '--plugin-build')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.launcher.exists())
        self.assertNotIn('[s/N]', result.stdout)
        self.assertIn('--tools-only', result.stdout)
