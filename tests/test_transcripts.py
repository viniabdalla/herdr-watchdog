"""Reader contracts: append-only cursor, bounded work and replacement recovery."""
import json
from pathlib import Path
import tempfile
import unittest

from watchdog_app.transcripts import Reader


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'history.jsonl'

    def test_incomplete_utf8_row_resumes_without_losing_the_previous_cursor(self):
        self.path.write_bytes(b'{"n":1}\n{"text":"caf\xc3')
        reader = Reader(self.path)
        first = reader.read()
        self.assertEqual(first.records, [{'n': 1}])
        cursor = reader.cursor
        self.assertEqual(reader.read().records, [])
        self.assertEqual(reader.cursor, cursor)
        with self.path.open('ab') as file: file.write(b'\xa9"}\n')
        self.assertEqual(reader.read().records, [{'text': 'caf\u00e9'}])
        self.assertFalse(reader.read().catching_up)

    def test_invalid_and_oversize_lines_do_not_block_subsequent_events(self):
        self.path.write_bytes(b'null\n[]\nnot json\n'+b'x'*200+b'\n{"n":2}\n')
        reader = Reader(self.path, budget=32, max_line=64)
        records=[]
        for _ in range(12): records.extend(reader.read().records)
        self.assertEqual(records, [{'n': 2}])
        self.assertLessEqual(len(reader.pending), 64)

    def test_bounded_catchup_and_idle_read_do_not_replay(self):
        self.path.write_text(''.join(json.dumps({'n': n})+'\n' for n in range(100)))
        reader = Reader(self.path, budget=64)
        batch = reader.read()
        self.assertTrue(batch.catching_up)
        records=batch.records
        for _ in range(30): records += reader.read().records
        self.assertEqual([r['n'] for r in records], list(range(100)))
        self.assertEqual(reader.read().records, [])

    def test_rotation_truncation_and_same_inode_rewrite_reset_generation(self):
        self.path.write_text('{"old":1}\n')
        reader=Reader(self.path);reader.read()
        replacement=self.path.with_suffix('.new');replacement.write_text('{"new":2}\n')
        replacement.replace(self.path)
        batch=reader.read();self.assertTrue(batch.reset);self.assertEqual(batch.records,[{'new':2}])
        self.path.write_text('{}\n')
        self.assertTrue(reader.read().reset)
        self.path.write_text('{"rewritten":3}\n')
        batch=reader.read();self.assertTrue(batch.reset);self.assertEqual(batch.records,[{'rewritten':3}])

    def test_missing_source_does_not_preserve_old_records(self):
        self.path.write_text('{}\n');reader=Reader(self.path);reader.read()
        self.path.unlink();batch=reader.read()
        self.assertTrue(batch.unavailable);self.assertTrue(batch.reset)

    def test_prefix_rewrite_with_unchanged_tail_is_a_new_source(self):
        self.path.write_text('{"n":1}\n'+'{}\n'*100)
        reader=Reader(self.path);reader.read()
        self.path.write_text('{"n":2}\n'+'{}\n'*100)
        batch=reader.read()
        self.assertTrue(batch.reset)
        self.assertEqual(batch.records[0], {'n':2})

    def test_non_regular_source_cannot_block_the_ui(self):
        import os, subprocess, sys
        os.mkfifo(self.path)
        result=subprocess.run([sys.executable,'-B','-c',
            'from watchdog_app.transcripts import Reader; import sys; print(bool(Reader(sys.argv[1]).read().unavailable))',
            str(self.path)],capture_output=True,text=True,timeout=2)
        self.assertEqual(result.stdout.strip(),'True')

    def test_invalid_gap_does_not_replay_valid_records_before_missing_data(self):
        self.path.write_text('{"old":1}\nbroken\n{"new":2}\n')
        batch=Reader(self.path).read()
        self.assertTrue(batch.discarded)
        self.assertEqual(batch.records,[{'new':2}])
