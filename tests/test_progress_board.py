"""Spec #21 (docs/issues/21-spec-progress-agentes.md): AGENTES shows who does what, and where."""
import json
import os
from pathlib import Path
import time
import unittest
from unittest.mock import patch

import test_progress_agents


class FakeApi:
    def __init__(self, live):
        self.live, self.calls = live, []

    def call(self, *args):
        self.calls.append(args)
        if args[:2] == ('pane', 'get'):
            return {'pane': next(p for p in self.live if p['pane_id'] == args[2])}
        return {}


class BoardTests(test_progress_agents.ProgressAgentsTests):
    def items(self, monitor=None):
        monitor = monitor or self.monitor()
        return monitor, monitor.poll()

    def find(self, source, prefix):
        return next((text, color, item) for text, color, item in source if text.startswith(prefix))

    def add_worker(self, ticket, pane, terminal, *, group='a'*40, leader=None, tab='w:t2', leva='Leva', status='working'):
        from dataclasses import replace
        from watchdog_app import bindings
        actor = replace(self.worker, pane=pane, terminal=terminal, session='s-'+ticket)
        record = dict(self.record, ticket=ticket, pane=pane, terminal=terminal, group=group,
                      leader=leader or self.leader.pane, tab=tab, leva=leva)
        self.live.append(dict(self.live[1], pane_id=pane, terminal_id=terminal, agent_status=status,
                              agent_session={'kind': 'id', 'value': actor.session}))
        self.extra.append(record)
        self.actors.append(actor)
        return record

    def setUp(self):
        super().setUp()
        self.extra, self.actors = [], []
        self.record.update(tab='w:t2', leva='Leva 1 · Base')
        patch('watchdog_app.leader_kit.executors',
              side_effect=lambda repo, group=None: {'executors': [self.record] + self.extra}).start()
        from types import SimpleNamespace as NS
        from test_actions import FakeBinding
        patch('watchdog_app.bindings.engine', return_value=NS(Binding=FakeBinding, verify=lambda b: None,
              candidates=lambda: ([self.leader, self.worker] + self.actors, []))).start()

    def test_order_blocked_block_then_leader_then_tab_groups(self):
        # Spec #21 L32-34,53: blocked, queued and Herdr-blocked first, in red, above the leader.
        self.add_worker('T9', 'w:p9', 't9', status='blocked')
        self.extra.append(dict(self.record, ticket='T8', pane='w:p8', terminal='t8', state='failed', error='abrir falhou'))
        self.record['blocked'] = {'reason': 'qual aba usar?', 'at': time.time()}
        self.live[1]['agent_status'] = 'idle'
        _, source = self.items()
        text = [t for t, _, _ in source]
        start, leader = text.index('BLOQUEADOS'), next(i for i, t in enumerate(text) if t.startswith('Líder ·'))
        block = text[start:leader]
        for expected in ('T1 · w:p2', 'qual aba usar?', 'T9 · w:p9', 'T8', 'abrir falhou', 'T2', 'na fila', 'T3'):
            self.assertTrue(any(expected in t for t in block), (expected, block))
        self.assertTrue(all(color == 'blocked' for t, color, _ in source[start:leader] if t))
        queued = self.find(source, 'T2')[2]
        self.assertEqual(queued.state, 'queued')
        self.assertIn('na fila', self.find(source, 'T2')[0])

    def test_workers_of_any_leader_round_grouped_by_tab_and_others(self):
        # Spec #21 L35-36,51-52: other rounds of the same leader appear; foreign ones go to Outros.
        self.add_worker('Religar-18', 'w:pW', 'tW', group='spec-17', tab='w:tC', leva='Religar Codex')
        self.add_worker('X1', 'w:pX', 'tX', group='alheio', leader='w:p99', tab='w:tZ', leva='Outra')
        monitor, source = self.items()
        text = [t for t, _, _ in source]
        header = next(i for i, t in enumerate(text) if 'tC · Religar Codex' in t)
        self.assertTrue(text[header].startswith('▾'))
        self.assertTrue(text[header + 1].startswith('Religar-18 · w:pW · Trabalhando'))
        others = next(t for t in text if 'Outros' in t)
        self.assertTrue(others.startswith('▸'))
        self.assertFalse(any(t.startswith('X1 ·') for t in text))
        monitor.toggle('outros')
        self.assertTrue(any(t.startswith('X1 ·') for t, _, _ in monitor.poll()))

    def test_idle_group_starts_collapsed_with_summary_and_toggles(self):
        # Spec #21 L36,59: a group with nobody working starts collapsed, with a summary.
        self.add_worker('R1', 'w:pR', 'tR', tab='w:t8', leva='Code Review', status='idle')
        self.add_worker('R2', 'w:pS', 'tS', tab='w:t8', leva='Code Review', status='idle')
        monitor, source = self.items()
        header = next(t for t, _, _ in source if 't8 · Code Review' in t)
        self.assertTrue(header.startswith('▸'))
        self.assertIn('2 ociosos', header)
        self.assertFalse(any(t.startswith('R1 ·') for t, _, _ in source))
        item = next(i for t, _, i in source if 't8 · Code Review' in t)
        monitor.toggle(item.group)
        self.assertTrue(any(t.startswith('R1 ·') for t, _, _ in monitor.poll()))

    def test_closed_pane_is_hidden(self):
        # Spec #21 L36: workers whose pane was closed do not appear.
        self.live[1]['terminal_id'] = 'replaced'
        _, source = self.items()
        self.assertFalse(any(t.startswith('T1 ·') for t, _, _ in source))

    def test_working_agent_has_activity_line_and_level_colored_context(self):
        # Spec #21 L37-39,58: dot by state, bar by context level, one detail line while working.
        _, source = self.items()
        index = next(i for i, (t, _, _) in enumerate(source) if t.startswith('T1 ·'))
        text, color, item = source[index]
        self.assertEqual(item.state, 'working')
        self.assertIsNone(color)
        self.assertEqual(dict(item.segments)[next(s for s, _ in item.segments if '▰' in s)], 'level_ok')
        detail = source[index + 1]
        self.assertTrue(detail[0].startswith('  '))
        self.assertIn('T1 (#2) — Work', detail[0])
        for context, level in ((85000, 'level_warn'), (100000, 'level_full')):
            self.history.write_text(self.history.read_text().replace('12000', str(context)))
            _, source = self.items()
            item = self.find(source, 'T1 ·')[2]
            self.assertIn(level, [c for _, c in item.segments])
            self.history.write_text(self.history.read_text().replace(str(context), '12000'))
        self.live[1]['agent_status'] = 'idle'
        monitor, _ = self.items()
        monitor.toggle('w:t2')
        source = monitor.poll()
        index = next(i for i, (t, _, _) in enumerate(source) if t.startswith('T1 ·'))
        self.assertEqual(source[index][2].state, 'idle')
        self.assertFalse(source[index + 1][0].startswith('  '))

    def test_done_states(self):
        # Spec #21 L37: done = TODO task done, or `pronto` sent while the worker is stopped.
        (self.repo/'TODO.md').write_text((self.repo/'TODO.md').read_text().replace('- [ ] T1', '- [x] T1'))
        self.live[1]['agent_status'] = 'idle'
        self.add_worker('R1', 'w:pR', 'tR', status='idle')
        self.extra[-1]['ready'] = {'at': time.time()}
        monitor, source = self.items()
        self.assertIn('2 feitos', self.find(source, '▸ t2')[0])
        monitor.toggle('w:t2')
        source = monitor.poll()
        self.assertEqual(self.find(source, 'T1 ·')[2].state, 'done')
        self.assertIn('Feito', self.find(source, 'R1 ·')[0])

    def test_go_button_focuses_exact_pane(self):
        # Spec #21 L40,54: [ir] uses `agent focus` with the worker's pane.
        monitor, source = self.items()
        item = self.find(source, 'T1 ·')[2]
        api = FakeApi(self.live)
        monitor.go(item, api)
        self.assertEqual(api.calls, [('agent', 'focus', 'w:p2')])
        self.assertEqual(self.find(source, 'Líder ·')[2].pane, self.leader.pane)

    def test_close_only_idle_unblocked_worker_after_terminal_check(self):
        # Spec #21 L41,55-56: no close while working or blocked; idle closes the registered pane.
        monitor, source = self.items()
        self.assertFalse(self.find(source, 'T1 ·')[2].closable)
        self.assertFalse(self.find(source, 'Líder ·')[2].closable)
        self.live[1]['agent_status'] = 'idle'
        self.record['blocked'] = {'reason': 'dúvida', 'at': time.time()}
        self.assertFalse(self.find(monitor.poll(), 'T1 ·')[2].closable)
        del self.record['blocked']
        monitor.poll()
        monitor.toggle('w:t2')  # idle group starts collapsed (L36)
        item = self.find(monitor.poll(), 'T1 ·')[2]
        self.assertTrue(item.closable)
        api = FakeApi(self.live)
        self.live[1]['terminal_id'] = 'other'
        with self.assertRaises(RuntimeError):
            monitor.close(item, api)
        self.assertNotIn(('pane', 'close', 'w:p2'), api.calls)
        self.live[1]['terminal_id'] = 't2'
        monitor.close(item, api)
        self.assertEqual(api.calls[-1], ('pane', 'close', 'w:p2'))

    def test_unblock_prompt_goes_to_leader_once(self):
        # Spec #21 L42,57: one delivery with contract and rule; a repeat only reports it was sent.
        self.record.update(blocked={'reason': 'qual aba usar?', 'at': time.time()},
                           contract='/abs/contrato.md')
        self.live[1]['agent_status'] = 'idle'
        monitor, source = self.items()
        item = self.find(source, 'T1 ·')[2]
        sent = []
        first = monitor.unblock(item, send=lambda pane, text: sent.append((pane, text)))
        second = monitor.unblock(item, send=lambda pane, text: sent.append((pane, text)))
        self.assertEqual(len(sent), 1)
        pane, text = sent[0]
        self.assertEqual(pane, self.leader.pane)
        for expected in ('[Unblock · T1]', 'w:p2', 'qual aba usar?', '/abs/contrato.md',
                         'imperativo', 'sugestão', 'kit desbloquear'):
            self.assertIn(expected, text)
        self.assertIn('enviado', first)
        self.assertIn('já', second)
        queued = self.find(source, 'T2')[2]
        monitor.unblock(queued, send=lambda pane, text: sent.append((pane, text)))
        self.assertIn('na fila', sent[-1][1])

    def test_kit_unblock_and_notices_update_registry(self):
        # Spec #21 L33,42: BLOQUEIO marks, `pronto` and `kit desbloquear` clear the block.
        from watchdog_app import leader_kit
        from watchdog_app.store import atomic
        patch.stopall()
        patch.dict(os.environ, WATCHDOG_STATE_DIR=str(self.repo/'state')).start()
        self.addCleanup(patch.stopall)
        target = self.repo/'.watchdog/executors.json'
        atomic(target, {'version': 1, 'project': str(self.repo), 'executors': [self.record]})
        leader_kit.mark_notice(self.tree, pane='w:p2', ticket='T1', event='BLOQUEIO', detail='qual aba?')
        record = json.loads(target.read_text())['executors'][0]
        self.assertEqual(record['blocked']['reason'], 'qual aba?')
        leader_kit.unblock(self.repo, group='a'*40, ticket='T1')
        self.assertNotIn('blocked', json.loads(target.read_text())['executors'][0])
        leader_kit.mark_notice(self.tree, pane='w:p2', ticket='T1', event='BLOQUEIO', detail='de novo')
        leader_kit.mark_notice(self.tree, pane='w:p2', ticket='T1', event='pronto', detail='abc')
        record = json.loads(target.read_text())['executors'][0]
        self.assertNotIn('blocked', record)
        self.assertIn('ready', record)
        leader_kit.mark_notice(self.repo/'nowhere', pane='w:p9', ticket='T9', event='pronto', detail='x')

    def test_working_long_after_block_leaves_red_block(self):
        # Spec #21 L33: a worker working for over a minute after BLOQUEIO is no longer blocked.
        self.record['blocked'] = {'reason': 'dúvida', 'at': time.time() - 120}
        self.assertEqual(self.find(self.items()[1], 'T1 ·')[2].state, 'working')
        self.record['blocked']['at'] = time.time()
        self.assertEqual(self.find(self.items()[1], 'T1 ·')[2].state, 'blocked')

    def test_goal_ended_banner_leaves_top(self):
        # Spec #21 L32,60: the ended banner is not at the top; the final summary stays at the end.
        from watchdog_app import long_run
        from watchdog_app.store import atomic
        state = long_run.record(self.repo)
        state['notices'] = {'ended': {'title': 'Meta encerrada · 1 de 3', 'body': 'Concluída T1 · evidência: ok',
                                      'completed': [], 'blocked': []}}
        atomic(long_run.path_for(self.repo), state)
        text = [t for t, _, _ in self.items()[1]]
        banner = text.index('Meta encerrada · 1 de 3')
        self.assertLess(next(i for i, t in enumerate(text) if t.startswith('Líder ·')), banner)
        self.assertEqual(text[banner + 1], 'Concluída T1 · evidência: ok')


    def test_pty_clicks_go_select_and_close_with_y(self):
        # Spec #21 L40-41,54-56: only the exact [ir] click focuses; [fechar] needs Y.
        import fcntl, struct, termios
        from test_artifacts_yazi import Terminal
        log = self.repo/'hits.json'
        boot = """
import sys, json, curses
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import test_progress_board as m
f = m.BoardTests('test_go_button_focuses_exact_pane'); f.setUp()
f.add_worker('R1', 'w:pR', 'tR', status='idle')
log = Path(sys.argv[2]); calls = []
def call(self, *args):
    calls.append(list(args)); log.with_suffix('.calls').write_text(json.dumps(calls))
    if args[:2] == ('pane', 'list'): return {'panes': f.live}
    if args[:2] == ('pane', 'get'): return {'pane': next(p for p in f.live if p['pane_id'] == args[2])}
    return {}
from watchdog_app.herdr import Herdr
Herdr.call = call
import watchdog_app.progress_ui as ui
original, hits = ui.draw_item, {}
def draw(screen, y, width, item, *a, **k):
    result = original(screen, y, width, item, *a, **k)
    if item.ticket: hits[item.ticket] = [y, result]; log.write_text(json.dumps(hits))
    return result
ui.draw_item = draw
try: curses.wrapper(ui.panel, f.repo, f.file)
finally: f.doCleanups()
"""
        terminal = Terminal(['python3', '-c', boot, str(Path(__file__).parent), str(log)],
                            dict(os.environ, TERM='xterm-256color'))
        self.addCleanup(terminal.close)
        fcntl.ioctl(terminal.master, termios.TIOCSWINSZ, struct.pack('HHHH', 30, 120, 0, 0))

        def until(check, timeout=10):
            end = time.monotonic() + timeout
            while time.monotonic() < end:
                terminal.wait_for('\x00', timeout=.2)
                try:
                    value = check()
                except (OSError, ValueError, KeyError, StopIteration):
                    value = None
                if value:
                    return value
            self.fail(terminal.output.decode(errors='replace')[-2000:])

        def hits():
            return json.loads(log.read_text())

        def calls():
            path = log.with_suffix('.calls')
            return json.loads(path.read_text()) if path.exists() else []

        def click(x, y):
            os.write(terminal.master, f'\x1b[<0;{x + 1};{y + 1}M\x1b[<0;{x + 1};{y + 1}m'.encode())

        until(lambda: 'T1' in hits() and 'R1' in hits())
        y, buttons = hits()['T1']
        click(4, y)
        time.sleep(1.5); terminal.wait_for('\x00', timeout=.2)
        self.assertNotIn(['agent', 'focus', 'w:p2'], calls())
        self.assertEqual([b[0] for b in hits()['T1'][1]], ['ir'])  # working: no [fechar]
        name, x0, _ = buttons[0]
        click(x0, y)
        until(lambda: ['agent', 'focus', 'w:p2'] in calls())
        y = hits()['R1'][0]
        click(4, y)
        fechar = until(lambda: next(b for b in hits()['R1'][1] if b[0] == 'fechar'))
        click(fechar[1], y)
        self.assertTrue(terminal.wait_for('Y confirma'), terminal.output.decode(errors='replace')[-2000:])
        os.write(terminal.master, b'n')
        self.assertTrue(terminal.wait_for('cancelado'))
        self.assertNotIn(['pane', 'close', 'w:pR'], calls())
        click(fechar[1], y)
        until(lambda: terminal.output.count(b'Y confirma') >= 2)
        os.write(terminal.master, b'Y')
        until(lambda: ['pane', 'close', 'w:pR'] in calls())
        os.write(terminal.master, b'q')
        self.assertEqual(terminal.process.wait(timeout=5), 0)

    def test_unverified_leader_still_lists_workers_without_usage(self):
        # Spec #21 L32,36: AGENTES keeps who/where when the leader cannot be verified.
        self.record['workspace'] = 'w'
        self.file.write_text(json.dumps({'repo': '/elsewhere', 'binding': {}}))
        _, source = self.items()
        self.assertTrue(any(t.startswith('Líder · — ·') for t, _, _ in source))
        line = self.find(source, 'T1 ·')[0]
        self.assertIn('Trabalhando', line)
        self.assertNotIn('12%', line)

# Reuse the fixture only; the inherited Spec #1 tests run in their own module.
for _name in [n for n in dir(test_progress_agents.ProgressAgentsTests) if n.startswith('test_')]:
    setattr(BoardTests, _name, None)


if __name__ == '__main__':
    unittest.main()
