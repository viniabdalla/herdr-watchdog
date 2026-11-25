"""Spec #1 L102-104,114,143,153,162: installed merge-danger in real PTYs."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

import test_matt_skills

ROOT = Path(__file__).resolve().parents[1]


class MergeDangerTests(test_matt_skills.MattSkillsTerminalTests):
    # Inherit the isolated fixture, not the scenarios of T7.
    test_prefix_visibility_edit_cancel_and_confirm = None
    test_spec_prefill_warning_and_narrow_terminal = None
    test_account_skill_and_tracker_local_section = None
    test_harness_excludes_other_roots_and_uninstalled_skill = None
    test_all_buttons_account_and_ancestor_roots_keep_task_shortcuts = None
    test_uninstalled_after_preview_refuses_delivery = None

    def installer(self):
        return subprocess.run([sys.executable, str(ROOT/'install-skills.py'),
                               '--claude-skills-dir', str(self.repo/'.claude/skills'),
                               '--codex-skills-dir', str(self.repo/'.agents/skills')],
                              env=self.env, capture_output=True, text=True)

    def test_installed_button_confirms_harness_command_in_both_modes(self):
        # Spec #1 L102-104,114,143,153,162: real installer -> strip -> fake Herdr.
        result = self.installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.installer().returncode, 0)  # repeated install is safe
        for kind, full in (('claude', False), ('codex', True)):
            with self.subTest(kind=kind):
                terminal = self.open(kind=kind, full=full)
                command = ('/' if kind == 'claude' else '$') + 'merge-danger'
                self.wait(terminal, command)
                before = len(self.commands())
                os.write(terminal.master, b'6')
                self.wait(terminal, 'Editar comando')
                self.assertEqual(len(self.commands()), before)
                os.write(terminal.master, b' integration-base..integration\r')
                self.wait(terminal, 'Skill enviada')
                self.assertEqual(self.commands()[-2][3], command + ' integration-base..integration')
                self.assertEqual(self.commands()[-1], ['pane', 'send-keys', 'project:p4', 'Enter'])
                terminal.close()

    def test_installer_preserves_unrelated_skill_without_partial_install(self):
        # Spec #1 L143: installation cannot replace the leader's own skill.
        target = self.repo/'.agents/skills/merge-danger/SKILL.md'
        target.parent.mkdir(parents=True)
        target.write_text('User-owned skill')
        result = self.installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Refusing to overwrite another skill', result.stderr)
        self.assertEqual(target.read_text(), 'User-owned skill')
        self.assertFalse((self.repo/'.claude/skills/merge-danger').exists())

    def test_absent_merge_danger_is_hidden_and_cannot_send(self):
        # Spec #1 L104,162: absent skill cannot dispatch a command.
        terminal = self.open()
        os.write(terminal.master, b'6')
        self.wait(terminal, 'Skill indisponível')
        self.assertNotIn(b'$merge-danger', terminal.output)
        self.assertEqual(self.commands(), [])
