from pathlib import Path
import json
import tempfile
import unittest

from watchdog_app.todo import Snapshot, change


KEY = '613821eb-e1d7-4ae6-9f71-88534c73c843'
OTHER = '182fac66-323d-468e-b333-a21d2f039c2e'
HEADER = '---\nwatchdog_todo: 1\n---\n# TODO\n\n'
BLOCK = ('- [ ] Resolver o áudio\n'
         f'  ID: {KEY}\n'
         '  Resumo: Recuperar os áudios para continuar o atendimento.\n'
         '  Origem: pedido-humano\n'
         '  Referência: conversa atual\n'
         '  Execução:\n'
         '    Investigar a fila.\n'
         '    - [ ] Verificar o processo e preservar arquivos.\n'
         '  Aceite:\n'
         '    Demonstrar recuperação com evidência.\n')
TEXT = HEADER + '## Próximo\n' + BLOCK + '\n## Feito\n'


class FormatTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.state = self.repo / 'state'

    def read(self, text=TEXT):
        (self.repo / 'TODO.md').write_bytes(text.encode())
        return Snapshot.read(self.repo)

    def test_fields_are_deterministic_and_nested_checklist_is_not_another_task(self):
        snap = self.read()
        self.assertEqual(snap.format_version, 1)
        self.assertEqual(len(snap.tasks), 1)
        task = snap.tasks[0]
        self.assertEqual(task.id, KEY)
        self.assertEqual(task.title, 'Resolver o áudio')
        self.assertIn('atendimento', task.summary)
        self.assertIn('- [ ] Verificar', task.execution)
        self.assertIn('evidência', task.acceptance)
        self.assertEqual(task.origin, 'pedido-humano')
        self.assertEqual(task.reference, 'conversa atual')
        self.assertIn('Demonstrar recuperação', task.text)
        self.assertFalse(task.historical)

    def test_identity_survives_title_details_position_and_state_edits(self):
        for text in (TEXT.replace('Resolver o áudio', 'Continuar o atendimento'),
                     TEXT.replace('Investigar a fila.', 'Investigar a fila de novo.'),
                     TEXT.replace('## Próximo', '# Nota\n\n## Em andamento'),
                     TEXT.replace('## Próximo', '## Feito').replace('- [ ] Resolver', '- [x] Resolver')):
            with self.subTest(text=text):
                self.assertEqual(self.read(text).tasks[0].id, KEY)

    def test_invalid_schema_never_falls_back_to_legacy(self):
        variants = [TEXT.replace('watchdog_todo: 1', 'watchdog_todo: 2'),
                    TEXT.replace('watchdog_todo: 1', 'watchdog_todo: true'),
                    TEXT.replace('watchdog_todo: 1', 'watchdog_todo: 1\nwatchdog_todo: 1'),
                    TEXT.replace('  Origem: pedido-humano\n', ''),
                    TEXT.replace('  Resumo:', '  OutraCoisa:'),
                    TEXT.replace('  Resumo:', '  ID: ' + KEY + '\n  Resumo:'),
                    TEXT.replace(KEY, 'not-a-uuid'),
                    TEXT.replace('pedido-humano', 'autorizado-pela-ia'),
                    TEXT.replace('  Execução:', '  execução:'),
                    TEXT.replace('  Aceite:\n    Demonstrar recuperação com evidência.', '  Aceite:'),
                    TEXT.replace('## Próximo', '## Feito'),
                    TEXT.replace('- [ ] Resolver', '- [x] Resolver'),
                    TEXT.replace('## Próximo', '## EstadoInventado'),
                    TEXT.replace('\n## Feito', '\n' + BLOCK + '\n## Feito')]
        for text in variants:
            with self.subTest(text=text), self.assertRaisesRegex(RuntimeError, 'TODO|formato|linha|ID'):
                self.read(text)

    def test_legacy_behavior_and_fenced_examples_are_preserved(self):
        self.assertEqual(self.read('## Next\n- [ ] Original\n  Notes\n').format_version, 0)
        snap = self.read(TEXT + '\n```markdown\n' + TEXT + '```\n')
        self.assertEqual(len(snap.tasks), 1)

    def test_indented_fences_with_blank_lines_are_complete_execution_content(self):
        text = TEXT.replace('    Investigar a fila.',
                            '    ```python\n    print(1)\n\n    print(2)\n    ```')
        snap = self.read(text)
        self.assertEqual(len(snap.tasks), 1)
        self.assertIn('print(2)', snap.tasks[0].execution)

    def test_state_actions_preserve_uuid_and_fields_and_reason_is_separate(self):
        snap = self.read()
        for kind in ('start', 'blocked', 'next', 'done'):
            snap = change(snap, [{'kind': kind, 'id': KEY, 'reason': 'aguardando acesso'}], self.state)
            task = snap.tasks[0]
            self.assertEqual(task.id, KEY)
            self.assertEqual(task.title, 'Resolver o áudio')
            self.assertIn('recuperação', task.acceptance)
            if kind == 'blocked':
                self.assertEqual(task.reason, 'aguardando acesso')
        self.assertTrue(task.done)

    def test_add_requires_complete_fields_and_creates_uuid(self):
        snap = self.read()
        with self.assertRaisesRegex(RuntimeError, 'campos|fields|Resumo'):
            change(snap, [{'kind': 'add', 'text': 'Nova tarefa'}], self.state)
        snap = change(snap, [dict(kind='add', text='Nova tarefa', summary='Melhorar a entrega.',
                                  execution='Executar o diagnóstico.', acceptance='Comprovar a entrega.',
                                  origin='sugestao-agente')], self.state)
        self.assertEqual(len(snap.tasks), 2)
        self.assertNotEqual(snap.tasks[0].id, KEY)
        self.assertEqual(snap.tasks[0].origin, 'sugestao-agente')

    def test_crlf_actions_and_stale_edits_keep_existing_safety(self):
        snap = self.read(TEXT.replace('\n', '\r\n'))
        snap = change(snap, [{'kind': 'start', 'id': KEY}], self.state)
        self.assertNotIn(b'\n', snap.raw.replace(b'\r\n', b''))
        path = self.repo / 'TODO.md'
        path.write_bytes(snap.raw + b'\r\nConcurrent note\r\n')
        before = path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'changed'):
            change(snap, [{'kind': 'done', 'id': KEY}], self.state)
        self.assertEqual(path.read_bytes(), before)

    def test_parse_validates_without_writing_file(self):
        snap = Snapshot.parse(self.repo, TEXT.encode())
        self.assertEqual(snap.tasks[0].id, KEY)
        self.assertFalse((self.repo / 'TODO.md').exists())

    def test_invalid_titles_and_unclosed_examples_are_explicit_schema_errors(self):
        for text in (TEXT.replace('Resolver o áudio', ' '),
                     TEXT.replace('Resolver o áudio', 'x' * 501),
                     TEXT.replace('Resolver o áudio', 'Áudio\x1b'),
                     TEXT + '\n```markdown\nExample with no closing fence\n'):
            with self.subTest(text=text), self.assertRaises(RuntimeError):
                self.read(text)

    def test_malformed_migration_metadata_never_causes_unhandled_type_errors(self):
        base = dict(version=1, kind='identity', source_digest='a' * 64, ids={KEY: OTHER})
        for values in ({KEY: []}, {KEY: {}}, {KEY: None}, {KEY: KEY}, {'not-an-id': OTHER}):
            row = dict(base, ids=values)
            text = TEXT + '<!-- watchdog-migration: ' + json.dumps(row) + ' -->\n'
            with self.subTest(values=values), self.assertRaises(RuntimeError):
                self.read(text)
