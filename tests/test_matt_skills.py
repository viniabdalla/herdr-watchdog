"""Spec #1 L102-107,144,153,162: skills through an isolated real terminal."""
import fcntl
import json
import os
from pathlib import Path
import signal
import struct
import termios
import unittest

import test_group_dispatch


class MattSkillsTerminalTests(test_group_dispatch.GroupDispatchTests):
    # Reuse only the fixture/transport helpers, not the dispatch scenarios.
    test_first_dispatch_preview_cancel_then_delivery_group_and_integration_base = None
    test_dispatch_adds_and_deduplicates_preserving_base = None
    test_manual_group_action_is_gone = None
    test_legacy_list_group_remains_readable_and_dispatch_preserves_its_members = None

    def setUp(self):
        super().setUp()
        self.home = self.repo / 'home'
        self.home.mkdir()
        self.account = self.home / 'account'
        value = json.loads(self.binding.read_text())
        value['binding']['account'] = str(self.account)
        self.binding.write_text(json.dumps(value))
        self.env.update(HOME=str(self.home), CODEX_HOME=str(self.home/'wrong'),
                        CLAUDE_CONFIG_DIR=str(self.home/'wrong'))
        self.env.pop('WATCHDOG_CODEX_HOME', None)

    def install(self, root, name):
        skill = root / name / 'SKILL.md'
        skill.parent.mkdir(parents=True, exist_ok=True)
        skill.write_text('---\nname: ' + name + '\n---\nFixture skill\n')

    def test_prefix_visibility_edit_cancel_and_confirm(self):
        # Spec #1 L102-105,144,162: only leader-visible skills; editable before Enter.
        for kind in ('claude', 'codex'):
            with self.subTest(kind=kind):
                root = self.repo / ('.claude' if kind == 'claude' else '.agents') / 'skills'
                self.install(root, 'to-spec')
                terminal = self.open(kind=kind, full=kind == 'codex')
                self.wait(terminal, ('/' if kind == 'claude' else '$') + 'to-spec')
                self.assertNotIn(b'to-tickets', terminal.output)
                before = self.commands()
                os.write(terminal.master, b'2')
                self.wait(terminal, 'Editar comando')
                self.assertEqual(self.commands(), before)
                os.write(terminal.master, b'\x1b')
                self.wait(terminal, 'Cancelled')
                self.assertEqual(self.commands(), before)
                os.write(terminal.master, b'2\x15comando editado\r')
                self.wait(terminal, 'Skill enviada')
                self.assertEqual(self.commands()[-2][3], 'comando editado')
                self.assertEqual(self.commands()[-1], ['pane', 'send-keys', 'project:p4', 'Enter'])
                terminal.close()

    def test_spec_prefill_warning_and_narrow_terminal(self):
        # Spec #1 L106-107,153: spec found locally, tracker warning and narrow controls.
        self.install(self.home/'.agents/skills', 'to-tickets')
        docs = self.repo/'docs/issues'
        docs.mkdir(parents=True)
        (docs/'1-spec-feature.md').write_text('---\ntitle: "Spec: feature"\n---\nBody\n')
        terminal = self.open()
        self.wait(terminal, '$to-tickets')
        fcntl.ioctl(terminal.master, termios.TIOCSWINSZ, struct.pack('HHHH', 30, 40, 0, 0))
        os.kill(terminal.process.pid, signal.SIGWINCH)
        os.write(terminal.master, b'3')
        self.wait(terminal, 'Editar comando')
        self.wait(terminal, 'local das issues')
        os.write(terminal.master, b'\r')
        self.wait(terminal, 'Skill enviada')
        self.assertEqual(self.commands()[0][3], '$to-tickets docs/issues/1-spec-feature.md')

    def test_account_skill_and_tracker_local_section(self):
        # Spec #1 L104,107,144: account root, not panel's harness environment.
        self.install(self.account/'skills', 'to-spec')
        tracker = self.repo/'docs/agents/issue-tracker.md'
        tracker.parent.mkdir(parents=True)
        tracker.write_text('## Cópia local em `docs/issues/`\nAtualize a cópia.\n')
        terminal = self.open(kind='claude')
        self.wait(terminal, '/to-spec')
        os.write(terminal.master, b'2')
        self.wait(terminal, 'Editar comando')
        self.assertNotIn('não guarda cópia local'.encode(), terminal.output)

    def test_harness_excludes_other_roots_and_uninstalled_skill(self):
        # Spec #1 L104,144,162: Codex cannot see Claude or the panel account's skills.
        self.install(self.repo/'.claude/skills', 'to-spec')
        self.install(self.home/'wrong/skills', 'to-spec')
        terminal = self.open(kind='codex')
        os.write(terminal.master, b'2')
        self.wait(terminal, 'Skill indisponível')
        self.assertNotIn(b'$to-spec', terminal.output)
        self.assertEqual(self.commands(), [])

    def test_all_buttons_account_and_ancestor_roots_keep_task_shortcuts(self):
        # Spec #1 L102-105,144,153: global, ancestor and account skills share a strip.
        self.install(self.account/'skills', 'retro')
        self.install(self.home/'.agents/skills', 'grill-with-docs')
        self.install(self.repo/'.agents/skills', 'to-spec')
        self.install(self.repo/'.agents/skills', 'to-tickets')
        terminal = self.open(kind='codex')
        for name in ('grill-with-docs', 'to-spec', 'to-tickets', 'retro'):
            self.wait(terminal, '$' + name)
        os.write(terminal.master, b'4 extra\x7f!\r')
        self.wait(terminal, 'Skill enviada')
        self.assertEqual(self.commands()[0][3], '$retro extr!')
        terminal.output = b''
        os.write(terminal.master, b' v')
        self.wait(terminal, 'Verify Leader')
        self.assertEqual(len(self.commands()), 2)

    def test_uninstalled_after_preview_refuses_delivery(self):
        # Spec #1 L104-105: preview does not authorize a skill that disappeared.
        self.install(self.account/'skills', 'retro')
        terminal = self.open(kind='codex')
        self.wait(terminal, '$retro')
        os.write(terminal.master, b'4')
        self.wait(terminal, 'Editar comando')
        (self.account/'skills/retro/SKILL.md').unlink()
        os.write(terminal.master, b'\r')
        self.wait(terminal, 'Skill indisponível')
        self.assertEqual(self.commands(), [])
